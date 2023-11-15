import datetime
import socket
import random
from sqlite3 import Timestamp
import threading
import time
import uuid
from src.termui import TerminalUi
from src.network import NetworkHandler


class MainController(threading.Thread):
    def __init__(self) -> None:
        # self.terminal_ui = TerminalUi()

        self.counter = 0

        self.is_port_valid = False
        self.terminate_flag = threading.Event()

        # * data_buffer  -> Unsorted list, data append
        # * data_storage -> sorted list
        self.data_buffer = []
        self.data_storage = []

        # * text_buffer -> sorted str
        self.text_buffer = []
        self.text_buffer_update = False

        # * Network flag & networking
        self.network_handler = None
        self.is_online = False
        self.have_peer = False
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = None

        # * Peer
        self.peer_id = None
        self.peer_connection = None

        # * Encryption
        self.encryption = None
        # * lock send_to_view
        self.data_storage_lock = False

        self.terminal_ui = TerminalUi(callback=self.user_input_handler)

        super(MainController, self).__init__()

    # * PROCESS USER INPUT
    def process_user_input(self, user_input: str):
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
        else:
            # sending it to other if we have connection together and are online
            timestamp = datetime.datetime.now()
            self.add_data_buffer(
                source=self.username, message=user_input, timestamp=timestamp
            )
            if self.is_online and self.have_peer:
                # send it to peer
                # send  content
                if self.encryption == None:
                    self.send_to_peer(user_input, timestamp)

                # if encryption != None , then process it accordingly

    def process_username(self, username: str) -> str:
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
        try:
            port = int(port)
            if not (20000 <= port <= 21000):
                port = random.randint(20000, 21000)
        except ValueError:
            port = random.randint(20000, 21000)

        return port

    def process_network_message(self, source_id, dest_id, data):
        if isinstance(data, bytes):
            # further processing, for example encryption
            pass
        elif isinstance(data, str):
            self.add_data_buffer(source=source_id, message=str(data))
        elif isinstance(data, dict):
            self.add_data_buffer(
                source=source_id,
                message=data["content"],
                timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            )
            self.print_data_routine()

    # * Validation
    def validate_ip(self, ip: str) -> bool:
        """
        Validate ip

        :param self:        Instances attributes
        :param ip:          Ip address
        """
        try:
            socket.inet_aton(ip)
            return True
        except:
            return False

    def validate_port(self, port) -> bool:
        try:
            port = int(port)
            return True
        except ValueError:
            return False

    # * Send to peer
    def send_to_peer(self, data: str, timestamp: datetime.datetime):
        # here add timestamp
        # translate timestamp to iso
        package_format = {"timestamp": timestamp.isoformat(), "content": data}
        self.network_handler.send_to_node(package_format, self.peer_connection)

    # * add Data_Buffer && data storage && text_buffer
    def add_data_buffer(self, source, message, timestamp=datetime.datetime.now()):
        data = {
            "source": source,
            "timestamp": timestamp,
            "message": message,
        }
        self.data_buffer.append(data)

    def update_data_storage(self):
        if len(self.data_buffer) > 0:
            inter = self.data_buffer.copy()
            inter = self.quicksort_dict_in_list(inter)
            self.data_buffer = []
            self.data_storage = self.data_storage + inter
            # && update_text_buffer

    def update_text_buffer(self):
        self.text_buffer = []
        for elm in self.data_storage:
            self.text_buffer.append(self.create_text_from_data(elm))

    def reset_data_storage(self):
        self.data_storage = []

    def pop_data_storage(self, n: int):
        for i in range(n):
            self.data_storage.pop()

    def create_text_from_data(self, data: dict):
        text = "[{}][{}]: {}".format(
            data["source"], data["timestamp"].strftime("%H:%M"), data["message"]
        )
        return text

    def print_data_routine(self):
        self.update_data_storage()
        self.update_text_buffer()
        self.terminal_ui.text_buffer = self.text_buffer

    def update_peer_ui(self, info=None):
        if info is not None:
            self.terminal_ui.update_peer_info(
                self.terminal_ui.log_window_border, info=self.peer_id
            )
        else:
            self.terminal_ui.update_peer_info(self.terminal_ui.log_window_border)

    # * NETWORKING
    def get_port(self):
        # get port
        self.add_data_buffer(" sys ", message="Pick a port : ")
        self.print_data_routine()

    def start_network_handler(self):
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
        self.terminate_flag.set()

    def run(self):
        # run
        self.terminal_ui.start()

        # Get uname
        self.add_data_buffer(" sys ", message="Username max 5 char. : ")
        self.print_data_routine()

        # start NetworkHandler

        while not self.terminate_flag.is_set():
            self.print_data_routine()

        self.terminal_ui.stop()
        self.network_handler.stop()

        time.sleep(5)

        self.terminal_ui.join()
        self.network_handler.stop()

    # ? CALLBACK
    def user_input_handler(self, type, user_input):
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


if __name__ == "__main__":
    x = MainController()
    print(x.process_username("ULAN5"))
