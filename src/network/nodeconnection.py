import json
import socket
import threading
import time

# ToDo:
# 1. Implement more of it
#


class NodeConnection(threading.Thread):
    def __init__(self, main_node, sock: socket.socket, id: str, host: str, port: int):
        """
        Constructor of NodeConnection class
        Main function is to wait, socket packet
        Side function send packet

        :param main_node:       Node object, Node that create this NodeConnection
        :param sock:            socket.socket instances that connected to other client
        :param id:              ID of other client
        :param host:            IP address of other client
        :param port:            Port of other client
        """

        # * Main node, creator of this NodeConnection instances
        self.main_node = main_node

        # * sock, socket instances that connected to other client
        self.sock = sock
        self.sock.settimeout(10.0)

        # * id   : id of other client
        # * host : host of other client
        # * port : port of other client
        self.id = str(id)
        self.host = host
        self.port = port

        # * terminate_flag, flag for termination
        self.terminate_flag = threading.Event()

        # * EOT, End of Transmision
        self.EOT_CHAR = 0x04.to_bytes(1, "big")

        # * init NodeConnection ??
        super(NodeConnection, self).__init__()

        self.main_node.debug_print(
            "Node Connection : Started with {} @{}:{}".format(
                self.id, self.host, self.port
            )
        )

    def run(self):
        """
        The main loop function is to receive data
        When data received, node_message from main_node will be invoked

        :param self:    Instances attributes
        """
        buffer = b""

        while not self.terminate_flag.is_set():
            chunk = b""

            try:
                chunk = self.sock.recv(4096)

            except socket.timeout:
                self.main_node.debug_print("NodeConnection: timeout")

            #! Need to be more spesific if possible
            except Exception as e:
                self.terminate_flag.set()
                self.main_node.debug_print("Unexpected Error: {}".format(str(e)))

            if chunk != b"":
                buffer += chunk
                eot_pos = buffer.find(self.EOT_CHAR)

                # * So if eot found in buffer, we process it on while
                while eot_pos > 0:
                    # * packet should contain all buffer - EOT
                    # * buffer is reset to b"" since it slice end of bytes
                    packet = buffer[:eot_pos]
                    buffer = buffer[eot_pos + 1 :]

                    self.main_node.message_count_recv += 1

                    #
                    self.main_node.node_message(self, self.parse_packet(packet))

                    # reset EOT_POS
                    eot_pos = buffer.find(self.EOT_CHAR)

            time.sleep(0.1)

        # Stopping nodeConnection
        self.sock.settimeout(None)
        self.sock.close()
        self.main_node.node_disconnected(self)
        self.main_node.debug_print("NodeConnection: Stopped")

    def stop(self):
        """
        Stop this thread

        :param self:        Instances attributes
        """
        self.terminate_flag.set()

    def send(self, data, encoding="utf-8"):
        """
        Sending data to connected Node, through NodeConnection Instance on other side
        No compression

        :param self:        Instances attributes
        :param data:        str, dict as json, or bytes
        :param encoding:    encoding method
        """

        # * If data is str its quite straighforward
        if isinstance(data, str):
            try:
                encoded_data = data.encode(encoding) + self.EOT_CHAR
                self.sock.sendall(encoded_data)
                # * Send a callback func
            except Exception as e:
                self.main_node.debug_print(
                    "nodeconnetion send: Error sending data to node: {}".format(str(e))
                )
                self.stop()

        elif isinstance(data, dict):
            try:
                encoded_data = json.dumps(data).encode(encoding) + self.EOT_CHAR
                self.sock.sendall(encoded_data)

            # * Non serialize data in dict so dumps failed
            except TypeError as type_error:
                self.main_node.debug_print(
                    "nodeconnection send: The dict is invalid, \n{}".format(type_error)
                )

            except Exception as e:
                self.main_node.debug_print(
                    "nodeconnetion send: Error sending data to node: {}".format(str(e))
                )
                self.stop()

        elif isinstance(data, bytes):
            try:
                encoded_data = data + self.EOT_CHAR
                self.sock.sendall(encoded_data)
            except Exception as e:
                self.main_node.debug_print(
                    "nodeconnetion send: Error sending data to node: {}".format(str(e))
                )
                self.stop()
        else:
            self.main_node.debug_print(
                "nodeconnection send: Invalid datatype, str, dict or bytes is valid"
            )

    def parse_packet(self, packet: bytes):
        """
        Parse packet that received

        :param self:        Instances attributes
        :param packet:      packet received type:bytes

        :return:            parsed data, str or bytes
        """

        try:
            packet_decoded = packet.decode("utf-8")
            try:
                # this is dict
                return json.loads(packet_decoded)

            # * If its not json.dumps
            # * Probably just a raw string
            except json.decoder.JSONDecodeError:
                # this should be str
                return packet_decoded

            except UnicodeDecodeError:
                # this is bytes
                return packet

        # * If its not encoded with utf-8
        # * Means it serious data
        except UnicodeDecodeError:
            # this is bytes
            return packet

    # ? MAGIC FUNCTION
    def __str__(self) -> str:
        return "NodeConnection: {}:{} <-> {}:{} ({})".format(
            self.main_node.host, self.main_node.port, self.host, self.port, self.id
        )

    def __hash__(self):
        # Hash main_node.id + self.id
        return hash(self.main_node.id + self.id)
