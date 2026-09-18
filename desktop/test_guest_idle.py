"""Agent protocol loop regression tests without booting or modifying a VM."""
import io
import json
import os
import unittest
from unittest.mock import Mock

if os.name == 'posix':
    from guest.agent import Agent


@unittest.skipUnless(os.name == 'posix', 'Agent runs inside Linux guest only')
class GuestIdleTests(unittest.TestCase):
    def test_large_reply_is_not_truncated_on_partial_device_write(self):
        class PartialWriter:
            def __init__(self):
                self.data = bytearray()
            def write(self, data):
                count = min(7, len(data))
                self.data.extend(data[:count])
                return count
            def flush(self):
                pass
        stream = PartialWriter()
        message = {'id': 123, 'output': 'x' * 100000}
        Agent(stream).emit(message)
        self.assertEqual(json.loads(stream.data), message)
        self.assertTrue(stream.data.endswith(b'\n'))

    def test_disconnected_writer_does_not_spin(self):
        stream = Mock()
        stream.write.return_value = 0
        with self.assertRaises(OSError):
            Agent(stream).emit({'id': 1})
        stream.write.assert_called_once()

    def test_disconnected_channel_waits_instead_of_busy_looping(self):
        agent = Agent(io.BytesIO())
        agent.stopped = Mock()
        agent.stopped.is_set.side_effect = [False, False, True]
        agent.serve()
        self.assertEqual(agent.stopped.wait.call_count, 2)
        agent.stopped.wait.assert_called_with(0.25)

    def test_reconnect_is_processed_after_disconnect_wait(self):
        stream = Mock()
        stream.readline.side_effect = [b'', b'{"id":1,"action":"status"}\n']
        stream.write.side_effect = len
        agent = Agent(stream)
        agent.stopped = Mock()
        agent.stopped.is_set.side_effect = [False, False, True]
        agent.dispatch = Mock(return_value={'guest': 'shellground'})
        agent.serve()
        agent.stopped.wait.assert_called_once_with(0.25)
        agent.dispatch.assert_called_once_with({'id': 1, 'action': 'status'})
        self.assertEqual(json.loads(bytes(stream.write.call_args.args[0]))['id'], 1)


if __name__ == '__main__':
    unittest.main()
