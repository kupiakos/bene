from src.sim import Sim


class ReportHandler:
    @staticmethod
    def receive_packet(packet):
        print('%.3f' % float(packet.created), packet.ident, '%.3f' % Sim.scheduler.current_time())


