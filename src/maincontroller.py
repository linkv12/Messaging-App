import datetime
import socket
import random
import threading
import time
import uuid

from src.encrypt.elgamal import ElGamal
from src.termui import TerminalUi
from src.network import NetworkHandler


class MainController(threading.Thread):
    def __init__(self) -> None:
        """
        Constructor for MainController class

        :param self:    Attritbutes Instance
        """

        # * Counter for the amount
        # * input from user
        self.counter = 0

        # * Termination flag, stopping thread
        self.terminate_flag = threading.Event()

        # * data_buffer  -> Unsorted list, data append
        # * data_storage -> sorted list
        self.data_buffer = []
        self.data_storage = []

        # * text_buffer -> sorted str
        self.text_buffer = []
        self.text_buffer_update = False

        # * Network flag & networking info
        self.is_online = False
        self.is_port_valid = False
        self.have_peer = False
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = None

        # * Peer Info
        self.peer_id = None
        self.peer_connection = None

        # * Encryption
        self.is_encrypted = False
        self.encryption_message_flag = None
        self.encryption = None
        self.has_sent_pub_key = False

        self.peer_encryption_info = dict()  # peer_id, peer_encryption, peer_pubkey
        # peer_encryption object only for encrypt

        # * Supported Encryption
        self.pub_key_ending_bytes = {"eg": bytes("5eg", "UTF-16")}
        self.pub_key_unpacking = {"eg": ElGamal.unpack_public_key}
        self.encryption_function = {"eg": ElGamal.pack_to_bytes_message}

        # * Other component
        # * Terminal_UI -> User Interface
        # * Network Handlet -> Networking using socket
        self.terminal_ui = TerminalUi(callback=self.user_input_handler)
        self.network_handler = None

        super(MainController, self).__init__()

    # * PROCESS USER INPUT
    def process_user_input(self, user_input: str):
        """
        Process user input

        :param self:        Attributes Instance
        :param user_input:  Input from user
        """

        if user_input == "!quit":
            self.add_data_buffer(" sys ", "Closing....")
            self.stop()
        elif user_input.startswith("!conn"):
            # tring to make connection
            address_candidate = user_input.split("!conn")[-1].strip()
            temp = address_candidate.split(":")
            if len(temp) == 2:
                # seem right
                ip_candidate, port_candidate = temp
                # check ip & port valid
                ip_valid = self.validate_ip(ip_candidate)
                port_valid = self.validate_port(port_candidate)

                if ip_valid and port_valid:
                    if not self.have_peer:
                        port_candidate = int(port_candidate)
                        self.network_handler.connect_to_node(
                            ip_candidate, port_candidate
                        )
                        self.add_data_buffer(
                            source=" sys ",
                            message="Connecting to {}:{}".format(
                                ip_candidate, port_candidate
                            ),
                        )
                    else:
                        self.add_data_buffer(" sys ", "Already have peer!")
                else:
                    # not valid
                    self.add_data_buffer(" sys ", "Invalid IP address and/or Port")
            else:
                # not valid
                self.add_data_buffer(" sys ", "Invalid input, makesure ip:port")

        elif user_input.startswith("!encrypt"):
            encryption_candidate = user_input.split("!encrypt")[-1].strip()
            match encryption_candidate:
                case "eg":
                    self.is_encrypted = True
                    self.encryption = ElGamal()
                    self.encryption_message_flag = (
                        self.encryption.encrypted_message_bytes
                    )

                    # send pub_key to peer
                    self.add_data_buffer(" sys ", "Using ElGamal encryption")
                case _:
                    self.add_data_buffer(
                        source=" sys ",
                        message="{} is not valid encryption".format(
                            encryption_candidate
                        ),
                    )

        else:
            # sending it to other if we have connection together and are online
            timestamp = datetime.datetime.now()
            self.add_data_buffer(
                source=self.username, message=user_input, timestamp=timestamp
            )

            online_status = self.is_online and self.have_peer
            if online_status and self.is_encrypted and not self.has_sent_pub_key:
                public_key = self.encryption.pack_public_key()
                self.send_to_peer(public_key, datetime.datetime.now())
                self.has_sent_pub_key = True

            if online_status:
                if self.peer_id not in self.peer_encryption_info.keys():
                    self.send_to_peer(user_input, timestamp)
                else:
                    # which mean other have use encryption
                    peer_pub_key = self.peer_encryption_info[self.peer_id]["public_key"]
                    encrypt_message = self.peer_encryption_info[self.peer_id][
                        "encryption_function"
                    ](user_input, peer_pub_key)
                    self.send_to_peer(encrypt_message, timestamp)

                # if encryption != None , then process it accordingly

    def process_username(self, username: str) -> str:
        """
        Process user input which presumed to be username

        :param self:        Attributes Instance
        :param username:    String input from user, assumed username

        :return: valid username, 5 char and no special char
        """

        invalid_chars = "'\"\\:@#$!~%^&*()_+"
        for char_ in invalid_chars:
            username = username.replace(char_, "")
        random_uuid = str(uuid.uuid4())[:8]
        if len(username[:5]) < 5:
            username = username + random_uuid[: 5 - len(username)]
        else:
            username = username[:5]
        return username

    def process_port(self, port) -> int:
        """
        Process user input which presumed to be port

        :param self:        Attributes Instance
        :param port:        String input from user, assumed as port

        :return: valid port, between 20000 and 21000
        """
        try:
            port = int(port)
            if not (20000 <= port <= 21000):
                port = random.randint(20000, 21000)
        except ValueError:
            port = random.randint(20000, 21000)

        return port

    def process_network_message(self, source_id, dest_id, data):
        """
        Process data from our peer

        :param self:            Attributes Instance
        :param source_id:       Id of our peer, the sender
        :param dest_id:         Our Id, the receiver
        :param data:            Data that is sent
        """

        if isinstance(data, bytes):
            # further processing, for example encryption
            pass
        elif isinstance(data, str):
            self.add_data_buffer(source=source_id, message=str(data))

        # Default send to peer data type
        # but some error might occur and recv other type
        elif isinstance(data, dict):
            # anticipate if data send to peer is str or other
            if isinstance(data["content"], str):
                self.add_data_buffer(
                    source=source_id,
                    message=data["content"],
                    timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
                )
            # if content != str, maybe encrpted ?????
            # content == bytes than def encrypted ,
            # either message, or pubkey
            elif isinstance(data["content"], bytes):
                # what is this either pubkey or enc, message
                # check if it key or mess

                if self.encryption_message_flag is not None:
                    is_message_for_us = data["content"].endswith(
                        self.encryption_message_flag
                    )
                else:
                    is_message_for_us = False
                # are we use encryption ?
                if self.is_encrypted and is_message_for_us:
                    # check ending

                    ciphers = self.encryption.unpack_encrypted_message(data["content"])
                    message = self.encryption.decrypt(ciphers)

                    self.add_data_buffer(
                        source=source_id,
                        message=message,
                        timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
                    )
                else:
                    # probably pubkey exchange
                    encryption_type = None
                    for type, bytes_value in self.pub_key_ending_bytes.items():
                        if data["content"].endswith(bytes_value):
                            encryption_type = type

                    # unpack pub_key
                    pub_key = self.pub_key_unpacking[encryption_type](data["content"])

                    # so we now what our peer use as encryption
                    self.peer_encryption_info[source_id] = {
                        "public_key": pub_key,
                        "encryption_function": self.encryption_function[
                            encryption_type
                        ],
                    }

            self.print_data_routine()

    # * Validation
    def validate_ip(self, ip: str) -> bool:
        """
        Validate ip

        :param self:        Instances attributes
        :param ip:          Ip address

        :return:            True if valid, False if not
        """
        try:
            socket.inet_aton(ip)
            return True
        except:
            return False

    def validate_port(self, port) -> bool:
        """
        Validate port is it int?

        :param self:        Instances attributes
        :param port:        Port number

        :return:            True if valid, False if not
        """
        try:
            port = int(port)
            return True
        except ValueError:
            return False

    # * Send to peer
    def send_to_peer(self, data, timestamp: datetime.datetime):
        """
        Sending data to self.peer_connection, our peer
        Data by default will be str or bytes
        Str for raw message
        Bytes for encrypted message & pubkey

        :param self:        Attributes Instance
        :param data:        Data to send
        :param timestamp:   Timestamp when data created
        """

        # here add timestamp
        # translate timestamp to iso

        # data str is raw, no encryption
        if isinstance(data, str):
            package_format = {"timestamp": timestamp.isoformat(), "content": data}
            self.network_handler.send_to_node(package_format, self.peer_connection)

        # bytes can only be received from encryption class
        # as encode_to_bytes function
        elif isinstance(data, bytes):
            # should it be further packed ?
            package_format = {"timestamp": timestamp.isoformat(), "content": data}
            self.network_handler.send_to_node(package_format, self.peer_connection)

        # dict -> sending pubkey
        # {timestamp: datetime.datetime
        #  content  :
        # }

    # * add Data_Buffer && data storage && text_buffer
    def add_data_buffer(self, source, message, timestamp=datetime.datetime.now()):
        """
        Add data to self.data_buffer
        list of dict -> list<dict>

        :param self:        Attributes Instance
        :param source:      Source of the data, originator
        :param message:     Message, data to display in view
        :param timestamp:   Timestamp, default: now
        """

        data = {
            "source": source,
            "timestamp": timestamp,
            "message": message,
        }
        self.data_buffer.append(data)

    def update_data_storage(self):
        """
        Update self.data_storage
        Data taken from data_buffer will be copied & sorted
        Then added to the end of data_storage

        :param self:        Attributes Instance
        """

        if len(self.data_buffer) > 0:
            inter = self.data_buffer.copy()
            inter = self.quicksort_dict_in_list(inter)
            self.data_buffer = []
            self.data_storage = self.data_storage + inter

    def update_text_buffer(self, amount=30):
        """
        Update text_buffer content
        W/ data from data_stroage, translated to string form

        :param self:        Attributes Instance
        :param amount:      Amount of data to be processed
        """
        self.text_buffer = []
        for elm in self.data_storage.copy()[-1 * amount :]:
            self.text_buffer.append(self.create_text_from_data(elm))

    def reset_data_storage(self):
        """
        Reset data storage, empty it

        :param self:        Attributes Instance
        """
        self.data_storage = []

    def pop_data_storage(self, n: int):
        """
        Remove n amount of data
        from self.data_storage

        :param self:        Attributes Instance
        :param n:           Amount of data to remove
        """

        for i in range(n):
            self.data_storage.pop()

    def create_text_from_data(self, data: dict):
        """
        Format data to str
        From data in data storage

        :param self:        Attributes Instance
        :param data:        Data that needed to be formated

        :return:    Formatted str, from data:dict
        """

        text = "[{}][{}]: {}".format(
            data["source"], data["timestamp"].strftime("%H:%M"), data["message"]
        )
        return text

    def print_data_routine(self):
        """
        Method to print data to UI

        :param self:        Attributes Instance
        """

        self.update_data_storage()
        self.update_text_buffer()
        self.terminal_ui.text_buffer = self.text_buffer

    def update_peer_ui(self, info=None):
        """
        Update peer id, to UI

        :param self:        Attributes Instance
        :param info:        peer id, default:None
        """
        if info is not None:
            self.terminal_ui.update_peer_info(
                self.terminal_ui.log_window_border, info=self.peer_id
            )
        else:
            self.terminal_ui.update_peer_info(self.terminal_ui.log_window_border)

    # * NETWORKING
    def get_port(self):
        """
        Get port from user input

        :param self:        Attributes Instance
        """
        self.add_data_buffer(" sys ", message="Pick a port : ")
        self.print_data_routine()

    def start_network_handler(self):
        """
        Starting network handler, to handle networking

        :param self:        Attributes Instance
        """
        self.network_handler = NetworkHandler(
            self.host,
            self.port,
            callback=self.network_callback_handler,
            id=self.username,
        )
        self.network_handler.start()

        server_info = "Online @{}:{}".format(self.host, self.port)
        self.terminal_ui.update_server_info(
            win=self.terminal_ui.log_window_border, info=server_info
        )
        self.print_data_routine()

    # * Thread
    def stop(self):
        """
        Stop this thread, preparation to quit

        :param self:        Attributes Instance
        """

        self.terminate_flag.set()

    def run(self):
        """
        Main event loop for this class

        :param self:        Attributes Instance
        """
        self.terminal_ui.start()

        # Get uname
        self.add_data_buffer(" sys ", message="Username max 5 char. : ")
        self.print_data_routine()

        # start NetworkHandler

        while not self.terminate_flag.is_set():
            self.print_data_routine()

        # * Send stop request
        self.terminal_ui.stop()
        self.network_handler.stop()

        time.sleep(1)

        # * When finished, join it
        self.terminal_ui.join()
        self.network_handler.join()

    # ? CALLBACK
    def user_input_handler(self, type, user_input):
        """
        Handle callback from terminal UI

        :param self:        Attributes Instance
        :param type:        type of callback called from terminal UI
        :param user_input:  User input from terminal UI
        """
        if self.counter == 0:
            self.username = self.process_username(user_input)
            self.counter = self.counter + 1
            self.add_data_buffer(" sys ", "Welcome, {}".format(self.username))
            self.reset_data_storage()
            self.print_data_routine()

            # show username
            self.terminal_ui.update_user_info(
                self.terminal_ui.log_window_border, info=self.username
            )

            self.get_port()

        elif self.counter == 1:
            self.port = self.process_port(user_input)
            self.counter = self.counter + 1
            self.pop_data_storage(1)
            self.start_network_handler()
        else:
            self.process_user_input(user_input=user_input)
            # print("user_input_callback: ", user_input)

    def network_callback_handler(self, callback_type, source_id, dest_id, data):
        """
        Handle callback from Network Handler

        :param self:            Attributes Instance
        :param callback_type:   type of callback called from Node
        :param source_id:       source ID
        :param dest_id:         destination ID
        :param data:            data, that been sent from network handler

        """
        # (callback_type, source_id, dest_id, data)
        match callback_type:
            case "server_started":
                self.is_online = True
                self.add_data_buffer(" sys ", "Server started by {}".format(data))
            case "outbound_node_connected":
                # save peer_id
                self.peer_id = dest_id
                self.peer_connection = self.network_handler.conn_info[self.peer_id]
                self.have_peer = True
                self.add_data_buffer(" sys ", data)
                self.update_peer_ui(info=self.peer_id)

            case "outbound_node_disconnected":
                # delete peer
                self.peer_id = None
                self.peer_connection = None
                self.have_peer = False
                self.add_data_buffer(" sys ", data)
                self.update_peer_ui()

            case "inbound_node_connected":
                # save peer_id
                self.peer_id = source_id
                self.peer_connection = self.network_handler.conn_info[self.peer_id]
                self.have_peer = True
                self.add_data_buffer(" sys ", data)
                self.update_peer_ui(info=self.peer_id)

            case "inbound_node_disconnected":
                # delete peer
                self.peer_id = None
                self.peer_connection = None
                self.have_peer = False
                self.add_data_buffer(" sys ", data)
                self.update_peer_ui()

            case "node_message":
                self.process_network_message(source_id, dest_id, data)

    # * Utils
    def quicksort_dict_in_list(self, unsorted_list, key="timestamp") -> list:
        """
        Sort list with dict as element
        Using Quicksort in ascending order

        :param self:            Attributes Instance
        :param unsorted_list:   list that is not sorted
        :param key:             dict key, to be sorted
        """

        # ! KEY MUST BE VALID
        # use quicksort
        if len(unsorted_list) > 1:
            pivot_index = random.randint(0, len(unsorted_list) - 1)
            pivot = unsorted_list.pop(pivot_index)
            smaller = []
            larger = []

            for element in unsorted_list:
                if element[key] >= pivot[key]:
                    larger.append(element)
                else:
                    smaller.append(element)

            if smaller == []:
                larger = self.quicksort_dict_in_list(larger, key)
                return [pivot] + larger
            elif larger == []:
                smaller = self.quicksort_dict_in_list(smaller, key)
                return smaller + [pivot]
            else:
                smaller = self.quicksort_dict_in_list(smaller, key)
                larger = self.quicksort_dict_in_list(larger, key)
                return smaller + [pivot] + larger

        else:
            # Only one element, sorted
            return unsorted_list
