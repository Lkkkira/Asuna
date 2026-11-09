"""Packaged worker over real loopback HTTP, without Chrome profiles or real UI actions."""
import json
import concurrent.futures
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chrome_bridge import ProfileBridge


@unittest.skipUnless(shutil.which('node'),'Node is needed for the packaged worker fixture')
class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.bridge=ProfileBridge(self.temp.name,port=0)
        self.bridge.start()
        self.base='http://127.0.0.1:'+str(self.bridge.port)
        self.messages=queue.Queue()
        self.peer=subprocess.Popen([shutil.which('node'),str(Path(__file__).with_name('extension_transport_peer.js'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        def read():
            for line in self.peer.stdout:
                self.messages.put(json.loads(line))
        self.reader=threading.Thread(target=read,daemon=True)
        self.reader.start()
        self.send(type='start',base=self.base,token=self.bridge.token)
        self.message('started')
        self.wait_connected()

    def tearDown(self):
        if self.peer.poll() is None:
            self.send(type='quit')
            self.peer.wait(timeout=5)
        self.bridge.close()
        self.reader.join(timeout=2)
        self.peer.stdin.close();self.peer.stdout.close();self.peer.stderr.close()
        self.temp.cleanup()

    def send(self,**value):
        self.peer.stdin.write(json.dumps(value)+'\n');self.peer.stdin.flush()

    def message(self,event):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            value=self.messages.get(timeout=max(.01,deadline-time.monotonic()))
            if value.get('event')=='error':self.fail(value['error'])
            if value.get('event')==event:return value
        self.fail('Worker did not reply: '+event)

    def wait_connected(self):
        deadline=time.monotonic()+8
        while not self.bridge.connected() and time.monotonic()<deadline:time.sleep(.03)
        self.assertTrue(self.bridge.connected())

    def status(self):
        self.send(type='status');return self.message('status')

    def test_worker_reconnects_after_assistant_restart_using_the_existing_secret(self):
        token,port=self.bridge.token,self.bridge.port
        self.bridge.close()
        self.bridge=ProfileBridge(self.temp.name,port=port)
        self.bridge.start()
        self.assertEqual(self.bridge.token,token)
        self.wait_connected()
        self.assertIn('paused',self.bridge.call('media','pause')['detail'])
        self.assertEqual(len(self.status()['calls']),1)
        self.assertEqual(self.bridge.extension_version,'1.2.0')

    def test_pair_rotation_during_an_inflight_poll_does_not_leave_the_pump_stopped(self):
        self.bridge.pair_code='b'*64
        self.bridge.pair_deadline=time.monotonic()+30
        token=self.bridge.token
        self.send(type='pair',base=self.base,code=self.bridge.pair_code)
        self.assertTrue(self.message('paired')['ok'])
        self.assertNotEqual(token,self.bridge.token)
        self.assertIn('paused',self.bridge.call('media','pause')['detail'])
        self.assertEqual(len(self.status()['calls']),1)

    def test_wake_restores_the_real_tab_before_a_control_is_dispatched(self):
        self.bridge.last_seen=0
        with patch('browser_profile.settings',return_value={'profile_directory':'Profile 1'}),patch('browser_profile.launch',side_effect=lambda url,profile:self.send(type='wake',url=url)):
            self.assertIn('paused',self.bridge.call('media','pause')['detail'])
        state=self.status()
        self.assertEqual(len(state['calls']),1)
        self.assertEqual(state['calls'][0]['url'],'https://fixture.test/video')
        self.assertGreaterEqual(state['alarms'],1)

    def test_lost_result_acknowledgement_retries_delivery_without_repeating_the_action(self):
        self.send(type='drop_ack');self.message('armed')
        self.assertIn('paused',self.bridge.call('media','pause')['detail'])
        deadline=time.monotonic()+4
        state=self.status()
        while state['resultRequests']<2 and time.monotonic()<deadline:
            time.sleep(.1);state=self.status()
        self.assertEqual(state['resultRequests'],2)
        self.assertEqual(len(state['calls']),1)

    def test_wake_during_a_delayed_old_poll_error_restarts_without_waiting_for_an_alarm(self):
        self.send(type='hold_poll_error');self.message('armed')
        self.bridge.last_seen=0
        self.bridge.jobs.put(None)
        self.message('poll_held')
        with patch('browser_profile.settings',return_value={'profile_directory':'Profile 1'}), \
                patch('browser_profile.launch',side_effect=lambda url,profile:self.send(type='wake',url=url)), \
                concurrent.futures.ThreadPoolExecutor() as executor:
            future=executor.submit(self.bridge.call,'media','pause')
            self.assertTrue(self.message('wake')['ok'])
            self.send(type='release_poll')
            self.assertIn('paused',future.result(timeout=8)['detail'])
        self.assertEqual(len(self.status()['calls']),1)


if __name__=='__main__':unittest.main(verbosity=2)
