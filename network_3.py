import queue
import threading
import json


# wrapper class for a queue of packets
class Interface:
    # @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    # get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


# Implements a network layer packet.
class NetworkPacket:
    # packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    # @param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    # called when printing the object
    def __str__(self):
        return self.to_byte_S()

    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]
        return self(dst, prot_S, data_S)


# Implements a network host for receiving and transmitting data
class Host:
    # @param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination

    # called when printing the object
    def __str__(self):
        return self.addr

    # create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully

    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    # thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router
class Router:
    # @param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        # save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        # TODO: set up the routing table for connected hosts
        self.rt_tbl_D = {}      # {destination: {router: cost}}
        self.known_hosts = [self.name]
        print('%s: Initialized routing table' % self)
        for key in self.cost_D:
            self.rt_tbl_D[key] = {self.name: self.cost_D[key]}
        self.print_routes()
    lock = threading.Lock();
    # Print routing table
    # def print_routes(self):
    #     # TODO: print the routes as a two dimensional table
    #     self.lock.acquire()
    #     print()
    #     print(self.rt_tbl_D)
    #     headerLine = self.name + " | "
    #     selfLine = self.name + " | "
    #     # nextLine = self.rt_tbl_D
    #     for i in self.rt_tbl_D:
    #         headerLine += i + " | "
    #         if i == self.name:
    #             selfLine += " 0 " + " | "
    #         else:
    #             selfLine += str(list(dict(list(self.rt_tbl_D[i].values())[0]).values())[0]) + " | "
    #     print(headerLine)
    #     print(selfLine)
    #     print()
    #     self.lock.release()
        #print("full r table: ", self.rt_tbl_D)

    def print_routes(self):
        self.lock.acquire()
        print()
        print("Known Hosts: ", self.known_hosts)
        header = self.name + " | "
        for dest in self.rt_tbl_D.keys():
            header += dest + " | "
        print(header)
        for r in self.known_hosts:
            line = r + " | "
            for s in self.rt_tbl_D:
                cost = str(list(list(self.rt_tbl_D[s].values())[0].values()))
                if str(list(self.rt_tbl_D[s].keys())[0]) == r:
                    line += cost + " | "
                else:
                    line += "    | "
            print(line)
        print()
        self.lock.release()

    # called when printing the object
    def __str__(self):
        return self.name

    # look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))

    # forward the packet according to routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # print("############################## BEGIN FORWARDING ################################")
            # 1. Receive packet p on interface i
            # 2. Look up destination of p in rt_tbl_D
            # 3. Return interface from rt_tbl_D?
            router_name = list(self.rt_tbl_D[p.dst].keys())[0]
            router_name.strip()
            # print("dest: ", p.dst)
            #print("forwarding to : ", router_name)
            inter = list(dict(list(self.rt_tbl_D[p.dst].values())[0]).keys())[0]
            #print("Inter: ", inter)
            self.intf_L[inter].put(p.to_byte_S(), 'out', True)
            #print('%s: forwarding packet "%s" from interface %d to %d' % \
                #(self, p, i, inter))
            #print("############################## END FORWARDING ################################")
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    # send out route update
    # @param i Interface number on which to send out a routing update
    # TODO send routing update on all interfaces
    def send_routes(self, i):
        # TODO: Send out a routing table update
        # create a routing table update packet
        # "[through this router]:[i can reach this dest]:[with a cost of #];"
        encodedTable = ""
        for key in self.rt_tbl_D:
            encodedTable += "{}:{}:{};".format(self.name, key, str(list(self.rt_tbl_D[key].values())[0]))
            # encodedTable += "{}:{}:{};".format(self.name, key, str(self.rt_tbl_D[key]))
        p = NetworkPacket(0, 'control', encodedTable)
        try:
            #print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    # Update routing table based on a route update packet
    #  @param p Packet containing routing information
    #  @param i Interface packet was received on
    def update_routes(self, p, i):
        # print("############################## UPDATING ROUTES ################################")
        entries = p.data_S.split(";")
        entries = list(filter(None, entries))
        for entry in entries:
            items = entry.split(":")
            source = items[0]
            distance_to_router = list(self.cost_D[source].values())[0]
            dest = items[1]
            cost = int(str(items[2])[-1])
            print(source, "|", distance_to_router, "|", dest, "|", cost)
            # if source not already known
            if source not in self.known_hosts:
                self.known_hosts.append(source)
            # if destination is not in current routing table
            if dest not in self.rt_tbl_D:
                self.rt_tbl_D[dest] = {source : {i : (int(cost) + int(distance_to_router))}}
                # send routing update back to source router
                self.send_routes(i)
            else:
                # check if updated cost is lower than current
                currentCost = int(list(list(self.rt_tbl_D[dest].values())[0].values())[0]) + distance_to_router
                newCost = cost
                print(currentCost, newCost)
                if currentCost < newCost:
                    self.rt_tbl_D[dest] = {source: {i: (int(newCost) + int(distance_to_router))}}
        self.print_routes()
        #print('%s: Received routing update %s from interface %d' % (self, p, i))
        # print("############################## DONE UPDATING ################################")

    # thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
