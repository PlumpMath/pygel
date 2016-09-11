import socketqueue


IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP = (socketqueue.IN,
                                         socketqueue.OUT,
                                         socketqueue.PRI,
                                         socketqueue.ERR,
                                         socketqueue.HUP)

class EvtType(object):
    TIMER = 0
    IO = 1
    OTHER = 2
