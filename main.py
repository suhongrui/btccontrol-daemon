__author__ = 'adam'


from twisted.internet import reactor, protocol


class Comms(protocol.Protocol):
    """This is just about the simplest possible protocol"""

    def dataReceived(self, data):
        "Test, Echo all back"
        self.transport.write(data)
        if data == ""


def main():
    """This runs the protocol on port 8000"""
    factory = protocol.ServerFactory()
    factory.protocol = Comms
    reactor.listenTCP(8000,factory)
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
