import threading
import datetime
import socket
import time
import uuid

from .nodeconnection import NodeConnection


class Node(threading.Thread):
    def __init__(self, host, port, max_connection=1, id=None, callback=None):
        """
        Node class, construtor

        :param host:            The host we wanted Node to be started
        :param port:            The port of node we wanted
        :param max_connection:  Max amount of connection for this node to have
        :param id:              ID for this Node
        :param callback:        A func, that have (flag, Node, NodeConn, data)
                                flag:       str, function that call the callback
                                Node:       Node
                                NodeConn:   NodeConnection
                                data:       str, need to be parsed
        """
        # * init parent class
        super(Node, self).__init__()

        # * debug
        self.debug = False

        # * init host and port for self
        self.host = host
        self.port = port

        # * callback, event will be send to callback function for handling any callback function
        self.callback = callback

        # * check id is none
        if id is None:
            self.id = self.generate_random_id()
        else:
            self.id = str(id)  # ehh it can always convert to str

        # * max connection
        self.max_connection = max_connection

        # * terminate flag, flag for thread termination
        self.terminate_flag = threading.Event()

        # * socket instance for node
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # * connection with us
        # * inbound - (US) <- Them
        # * outbound- (US) -> Them
        self.node_inbound = set()
        self.node_outbound = set()

        # * Number of recv message
        self.message_count_recv = 0

        # * initialize server
        self.init_server()

        # * List that need to be reconnected on connection was lost
        self.reconnect_to_nodes = []

    @property
    def all_nodes(self):
        """
        Print all node that we connected

        :param self:        Instances attributes

        :return:            concate of node_inbound and node_outbound set
        """
        return self.node_inbound | self.node_outbound

    def debug_print(self, message: str):
        """
        Print debug message to console

        :param self:        Instances attributes
        :param message:     Debug message

        """
        if self.debug:
            time_now = datetime.datetime.now()
            print(
                "[DEBUG] [{}] [{}]: {}".format(
                    self.id, time_now.strftime("%H:%M:%S"), message
                )
            )

    def init_server(self):
        """
        Init server based on host and port

        :param self:        Instances attributes

        :result:            socket instances bind to host:port
        """
        self.debug_print(
            "Initializing node on port {}, with id: {}".format(self.port, self.id)
        )

        # set socket option on SOL_SOCKET level
        # SO_REUSEADDR = 1, so option SO_REUSEADDR
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind host and port to socket
        self.sock.bind((self.host, self.port))

        # set timeout for socket, wait for n second to raise timeout exception
        self.sock.settimeout(10.0)

        # listen to n amount of connection
        self.sock.listen(1)

        if self.callback is not None:
            self.server_started()

    def stop(self):
        """
        Stop this Node

        :param self:        Instances attributes
        """
        self.node_request_to_stop()
        self.terminate_flag.set()

    def run(self):
        """
        Run Node from threading.Thread parent class

        :param self:        Instances attributes
        """

        while not self.terminate_flag.is_set():
            try:
                #! DEBUG
                self.debug_print(
                    "Node {}: Waiting for incoming connection".format(self.id)
                )

                # * conn:           a socket instance
                # * client_address: tuple of (host, port)
                conn, client_adress = self.sock.accept()

                #! DEBUG
                self.debug_print(
                    "Total inbound connection: {}".format(str(len(self.node_inbound)))
                )

                if len(self.node_inbound) < self.max_connection:
                    connected_node_host = client_adress[0]
                    connected_node_port = client_adress[1]
                    # * Receive info from other node
                    connected_node_id = conn.recv(4096).decode("utf-8")
                    if ":" in connected_node_id:
                        (
                            connected_node_id,
                            connected_node_port,
                        ) = connected_node_id.split(":")

                    # * send our ID, they already know our host and port
                    conn.send(self.id.encode("utf-8"))

                    # * Create new NodeConnection
                    # * connection between client
                    thread_client = self.create_new_connection(
                        conn=conn,
                        id=connected_node_id,
                        host=connected_node_host,
                        port=connected_node_port,
                    )
                    thread_client.start()

                    self.node_inbound.add(thread_client)
                    self.inbound_node_connected(thread_client)
                else:
                    self.debug_print("New Connection closed: Exceed connection allowed")
                    conn.close()
            except socket.timeout:
                self.debug_print("Node: Connection timeout!")

            #! I cant anticipate what error will be raised
            except Exception as e:
                raise e

            self.reconnect_nodes()
            time.sleep(0.2)

        self.debug_print("Node Stopping...")

        # * Send stop command to node
        for node in self.node_inbound.copy():
            node.stop()
        for node in self.node_outbound.copy():
            node.stop()

        # * sleep waiting for stop to be done
        time.sleep(0.5)

        # * Join it all, waiting it
        for node in self.node_inbound.copy():
            node.join()
        for node in self.node_outbound.copy():
            node.join()

        self.sock.settimeout(None)
        self.sock.close()
        self.debug_print("Node {} has stopped".format(self.id))

    # * Sending Logic:
    def send_to_node(self, n: NodeConnection, data):
        """
        Sending data to n

        :param self:            Attributes Instance
        :param n:               NodeConnection instances, that data need to go
        :param data:            Data to send
        """
        if n in self.node_inbound or n in self.node_outbound:
            n.send(data=data)
        else:
            self.debug_print("send_to_node: Can't send data, node not found")

    # * NodeConnection creation & destruction & reconnection
    def node_disconnected(self, node):
        """
        Method to properly disconnecting

        :param self:    Instances attributes
        :param node:    NodeConnection instances, want to be disconnected
        """
        self.debug_print("node_disconnected: {}".format(node.id))

        if node in self.node_inbound:
            self.node_inbound.remove(node)
            self.inbound_node_disconnected(node)

        if node in self.node_outbound:
            self.node_outbound.remove(node)
            self.outbound_node_disconnected(node)

    def create_new_connection(self, conn: socket.socket, id: str, host: str, port: int):
        """
        Create new connection to Node

        :param self:    Instances attributes
        :param conn:    socket.socket Instances that have connection with us
        :param id:      ID of other client
        :param host:    Host of other client
        :param port:    Port of other client

        :return:        NodeConnection intances, an extension of threading.Thread class
        """
        return NodeConnection(main_node=self, sock=conn, id=id, host=host, port=port)

    def connect_with_node(self, host, port, reconnect=False):
        """
        Try to connect with node @host:port

        :param host:        IP address of node we are trying to connect
        :param port:        Port number
        :param reconnect:   bool value, a flag for reconnect

        :return:            bool value of success in connecting effort
                            False if connection failed
                            True  if connection success or already connected
        """
        func_name = "connect_with_node"
        if self.host == host and self.port == port:
            print("{}: Cannot connect with yourself".format(func_name))
            return False

        # check if other node already connected to us
        for node in self.node_outbound:
            if node.host == host and node.port == port:
                print(
                    "{}: Already connected with this node ({})".format(
                        func_name, node.id
                    )
                )
                return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.debug_print("connecting to {}:{}".format(host, port))

            # * attempt to connect host:port
            sock.connect((host, port))

            # * Basic info exchange
            # * Node trying to connect, aka node that call this function
            # * Will send id:port
            sock.send("{}:{}".format(self.id, self.port).encode("utf-8"))

            # * The other party will send us it's Id
            # * Since we already know it's host and port
            connected_node_id = sock.recv(4096).decode("utf-8")

            if self.id == connected_node_id:
                # ? WHAT, how its possible UUID random, is other use our ID
                print("{}: You cannot connect with yourself?".format(func_name))
                sock.send("CLOSING: Already have connection together".encode("utf-8"))
                sock.close()
                return True

            for node in self.node_inbound:
                if node.host == host and node.id == connected_node_id:
                    print(
                        "{}: This node ({}) is already connected".format(
                            func_name, node.id
                        )
                    )
                    sock.send(
                        "CLOSING: Already have connection together".encode("utf-8")
                    )
                    sock.close()
                    return True

            # * Create new NodeConnection
            # * connection between client
            thread_client = self.create_new_connection(
                conn=sock, id=connected_node_id, host=host, port=port
            )

            # * Start the NodeConnection
            thread_client.start()

            # * Add NodeConnection to node_outbound
            self.node_outbound.add(thread_client)
            # * call back, on node_outbound added
            self.outbound_node_connected(thread_client)
            if reconnect:
                self.debug_print(
                    "{}: Reconnection check is enabled on node {}:{}".format(
                        func_name, host, port
                    )
                )
                self.reconnect_to_nodes.append({"host": host, "port": port, "tries": 0})
                return True

        #! Need to be spesific exception, but I dont know what exception will ever be thrown
        except Exception as e:
            self.debug_print(
                "TcpServer.{}: Could not connect with node. {}".format(
                    func_name, str(e)
                )
            )
            return False

    def reconnect_nodes(self):
        """
        Try to connect to disconnected nodes

        :param self:    Instances object
        """

        func_name = "reconnect_nodes"
        for node_to_check in self.reconnect_to_nodes:
            # {"host": host, "port": port, "tries": 0}
            found_node = False
            self.debug_print(
                "{}: checking node {}:{}".format(
                    func_name, node_to_check["host"], node_to_check["port"]
                )
            )

            for node in self.node_outbound:
                if (
                    node.host == node_to_check["host"]
                    and node.port == node_to_check["port"]
                ):
                    found_node = True
                    node_to_check["tries"] = 0
                    self.debug_print(
                        "{}: Node {}:{} is still running".format(
                            func_name, node.host, node.port
                        )
                    )
            # * Node no longer connected so reconn
            if not found_node:
                node_to_check["tries"] += 1
                if self.node_reconnection_error(
                    node_to_check["host"].node_to_check["port"], node_to_check["tries"]
                ):
                    self.connect_with_node(node_to_check["host"], node_to_check["port"])
                else:
                    self.debug_print(
                        "{}: Removing {}:{} from reconnection list".format(
                            func_name, node_to_check["host"], node_to_check["port"]
                        )
                    )
                    self.reconnect_to_nodes.remove(node_to_check)

    # ? Callbacks
    def server_started(self):
        """ """
        func_name = "server_started"
        self.debug_print(
            "{}: {} @{}:{}".format(func_name, self.id, self.host, self.port)
        )
        if self.callback is not None:
            self.callback(func_name, self, None, "")

    def node_message(self, node, data):
        """
        Data received from other node, data need to be str?
        or can it be bytes

        :param self:    Instances attributes
        :param node:    Nodes that send the data, originator
        :param data:    Data that the Node received, data is either str, or json

        :return:        No return
        """
        self.debug_print("node_message {} : {}".format(node.id, str(data)))
        if self.callback is not None:
            self.callback("node_message", self, node, data)

    def outbound_node_connected(self, node):
        """
        Callback for new outbound connection

        :param self:    Instansce attributes
        :param node:    class:NodeConnection Instances

        """
        func_name = "outbound_node_connected"
        self.debug_print("{}: Node {} is connecting".format(func_name, node.id))
        if self.callback is not None:
            self.callback(func_name, self, node, "")

    def outbound_node_disconnected(self, node):
        """
        Callback for outbound disconnecting

        :param self:    Instansce attributes
        :param node:    class:NodeConnection Instances

        """
        func_name = "outbound_node_disconnected"
        self.debug_print("{}: Node {} is disconnecting".format(func_name, node.id))
        if self.callback is not None:
            self.callback(func_name, self, node, "")

    def inbound_node_connected(self, node):
        """
        Callback for new inbound connection

        :param self:    Instance attributes
        :param node:    class:NodeConnection Instances
        """
        func_name = "inbound_node_connected"
        self.debug_print("{}: Node {} is connecting".format(func_name, node.id))
        if self.callback is not None:
            self.callback(func_name, self, node, "")

    def inbound_node_disconnected(self, node):
        """
        Callback for inbound disconnection

        :param self:    Instance attributes
        :param node:    class:NodeConnection Instances
        """
        func_name = "inbound_node_disconnected"
        self.debug_print("{}: Node {} is disconnecting".format(func_name, node.id))
        if self.callback is not None:
            self.callback(func_name, self, node, "")

    def node_request_to_stop(self):
        """
        Callback for stopping node instances

        :param self:    Instance attributes
        """
        func_name = "node_request_to_stop"
        self.debug_print("{}: Node {} is stopping".format(func_name, self.id))
        if self.callback is not None:
            self.callback(func_name, self, None, "")

    def node_send_success(self, node):
        """
        Callback on message sent successfully

        :param self:    Instance attributes
        :param node:    class:NodeConnection Instances
        """
        func_name = "node_send_success"
        self.debug_print("{}: Success sent to {}".format(func_name, node.id))
        if self.callback is not None:
            self.callback(func_name, self, node, "")

    # * RECONN LOGIC
    def node_reconnection_error(self, host, port, tries):
        """
        Basic node reconnection logic, it will always reconnect
        Should be overriden on inheritance since it currently have no logic at all
        Logic idea:
            : retry only tries <5

        :param self:    Instance attributes
        :param host:    IP address of node we tried to reconnect
        :param port:    Port of node we tried to reconnect
        :param tries:   Number of tries already done, num of reconnect attempt

        """
        func_name = "node_reconnection_error"
        self.debug_print(
            "{}: Reconnecting to node {}:{} ,tries:{}".format(
                func_name, host, port, tries
            )
        )
        return True

    # ? MAGIC FUNCTION
    def __str__(self):
        """
        :return:        str representation for this Node instances
        """
        return "Node {} @{}:{}".format(self.id, self.host, self.port)

    # * Utility Function
    @staticmethod
    def generate_random_id():
        """
        Generate random ID for Node, incase no ID is supplied

        :return:        random :type:str
        """
        return str(uuid.uuid4())[:8]

    def total_connection(self) -> int:
        """
        Count the amount of connection this node have
        Incl. inbound and outbound

        :param self:    Instances attributes

        :return:        Total number of connection inclusive inbound + outbound
        """
        return len(self.node_inbound) + len(self.node_outbound)
