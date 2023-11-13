import datetime
import threading
import uuid


from .node import Node

# ? Is threading.Thread even needed ?
# ? Our upperclass, main_controller can send using it function
# ? The message will be passed through callback, what it need to be stay on ?


class NetworkHandler(threading.Thread):
    def __init__(self, host: str, port: str, callback=None, id=None):
        """
        Network Handler constructor

        :param self:        Attribute instances
        :param host:        IP address for networking
        :param port:        Port for networking
        :param callback:    Function to handle output from NetworkHandler
        :param id:          ID for network handler
        """
        self.debug = True
        self.terminate_flag = threading.Event()

        self.host = host
        self.port = port
        if id is not None:
            self.id = str(id)
        else:
            self.id = self.generate_random_id()

        self.callback = callback

        self.node = self.create_new_node()

        # id + nodeConnection
        self.conn_info = dict()

        super(NetworkHandler, self).__init__()

    def debug_print(self, message):
        """
        Print debug message to console

        :param self:        Instances attributes
        :param message:     Debug message

        """
        if self.debug:
            time_now = datetime.datetime.now()
            print(
                "[DEBUG] [{}] [{}]: {}".format(
                    self.id, time_now.strftime("%H:%M:%S"), str(message)
                )
            )

    def create_new_node(self):
        """
        Create new Node instances

        :return:    Node class instances
        """
        return Node(
            host=self.host, port=self.port, id=self.id, callback=self.node_callback
        )

    def send_to_all_nodes(self, data):
        """
        Send data to all connected node with us

        :param self:        Instances attributes
        :param data:        Data wanted to be send
        """

        for conn_id in self.conn_info.keys():
            self.send_to_node_with_id(conn_id, data)

    def send_to_node_with_id(self, dest_id, data):
        """
        Send data to Node.id = dest_id

        :param self:        Instances attributes
        :param dest_id:     Id of the Node destination
        :param data:        Data wanted to be send
        """

        node_connection = self.conn_info.get(dest_id, None)
        if node_connection is not None:
            self.node.send_to_node(node_connection, data)
        else:
            self.debug_print(
                "send_to_node_with_id: No connection with such id {}".format(dest_id)
            )

    def stop(self):
        """
        Stop this NetworkHandler

        :param self:        Instances attributes
        """
        self.terminate_flag.set()

    # * MAIN LOOP, THREAD
    def run(self):
        """
        Run this NetworkHandler

        :param self:        Instances attributes
        """

        a = 1
        # * Start node
        self.node.start()
        while not self.terminate_flag.is_set():
            a = 1

        # * Stopping node
        self.node.stop()

    def connect_to_node(self, host, port):
        # *
        self.node.connect_with_node(host=host, port=port, reconnect=True)

    # * Callback handler
    def node_callback(self, callback_type, main_node, node_connection, data):
        """

        Style guide :
            : callback_type         : Type of callback
            : source_id             : where is started us, other node, or sys
            : dest_id               : where it going ex: recv, will have us as dest_id
            : data                  : formatted str, dict or bytes

        :param self:                Attributes instance
        :param callback_type:       Type of callback, what happen
        :param main_node:           self.node
        :param node_connection:     NodeConnection
        :param data:                Data that passed (str, dict or bytes)
        """

        #   Logic Idea
        #       On connect, inbound or outbound -> have dict with key = id, and val = NodeConnection
        #
        #

        daemon_callback = ["node_send_success"]

        # *> Match Case for data processing
        match callback_type:
            # * When server started
            case "server_started":
                dest_id = main_node.id
                source_id = "sys"
                data = "{}: {} @{}:{}".format(
                    callback_type, main_node.id, main_node.host, main_node.port
                )

            # * When node connected & diconnected with us
            case "outbound_node_connected":
                dest_id = node_connection.id
                source_id = main_node.id
                data = "{}: {} <- {} @{}:{}".format(
                    callback_type,
                    main_node.id,
                    node_connection.id,
                    node_connection.host,
                    node_connection.port,
                )
                self.conn_info[node_connection.id] = node_connection

            case "outbound_node_disconnected":
                dest_id = node_connection.id
                source_id = main_node.id
                data = "{}: {} <# {} @{}:{}".format(
                    callback_type,
                    main_node.id,
                    node_connection.id,
                    node_connection.host,
                    node_connection.port,
                )
                self.conn_info.pop(node_connection.id, None)

            # * When we connected & diconnected with other node
            case "inbound_node_connected":
                dest_id = main_node.id
                source_id = node_connection.id
                data = "{}: {} -> {} @{}:{}".format(
                    callback_type,
                    main_node.id,
                    node_connection.id,
                    node_connection.host,
                    node_connection.port,
                )
                self.conn_info[node_connection.id] = node_connection

            case "inbound_node_disconnected":
                dest_id = main_node.id
                source_id = node_connection.id
                data = "{}: {} #> {} @{}:{}".format(
                    callback_type,
                    main_node.id,
                    node_connection.id,
                    node_connection.host,
                    node_connection.port,
                )
                self.conn_info.pop(node_connection.id, None)

            # * When data received from other
            case "node_message":
                dest_id = main_node.id
                source_id = node_connection.id
                data = data

            # * node is stopping
            case "node_request_to_stop":
                dest_id = main_node.id
                source_id = "sys"
                data = "Node {} is stopping...".format(main_node.id)

            # ! Daemon callback case
            # * On node successfully sending data
            case "node_send_success":
                dest_id = node_connection.id
                source_id = main_node.id

        # * Some callback are daemon
        # * So it's not escalated
        if self.callback is not None and callback_type not in daemon_callback:
            self.callback(callback_type, source_id, dest_id, data)
        else:
            self.debug_print(data)

    @staticmethod
    def generate_random_id():
        """
        Generate random ID for Node, incase no ID is supplied

        :return:        random :type:str
        """
        return str(uuid.uuid4())[:8]


if __name__ == "__main__":
    x = NetworkHandler("127.0.0.1", 5069, callback=None, id=None)
    y = NetworkHandler("127.0.0.1", 5069, callback=None, id=None)
