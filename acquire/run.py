# Start up a backend and two frontends: one for NetAcquire, one for HTTP 
# clients via Mongrel2.
# This script is meant to quickly get up and running, so I'm ok with the path 
# mangling going on here on a failed import.

from threading import Thread
try:
    import acquire
except ImportError:
    import os, sys
    path_here = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.realpath(os.path.join(path_here, '../')))
    sys.path.insert(1, os.path.realpath(os.path.join(path_here, '../lib')))
from acquire.backend import Backend
from acquire.netacquire import NetAcquire

settings = {
    'pub_address': 'tcp://127.0.0.1:16180',
    'push_address': 'tcp://127.0.0.1:27183',
    'netacquire_address': '127.0.0.1:31415',
    'netacquire_name': 'Acquire',
    'mongrel2_sender_id': 'd693a7cc-2bba-469a-b478-11a50ca09116',
    'mongrel2_send_spec': 'tcp://127.0.0.1:9999',
    'mongrel2_recv_spec': 'tcp://127.0.0.1:9998',
}

back = Backend()
back_settings = {
    'pub_address': settings['pub_address'],
    'pull_address': settings['push_address'],
}
back_thread = Thread(target=back.run, name='backend', kwargs=back_settings)
front = NetAcquire()
accept_address = settings['netacquire_address'].split(':')
accept_address = (accept_address[0], int(accept_address[1]))
front_settings = {
    'server_name': settings['netacquire_name'],
    'backend_sub_address': settings['pub_address'],
    'backend_push_address': settings['push_address'],
    'accept_address': accept_address,
}
front_thread = Thread(target=front.run, name='netacquire', 
                      kwargs=front_settings)
def http():
    from acquire.http import Mongrel2Handler
    h = Mongrel2Handler(settings['mongrel2_sender_id'], 
                        send_spec=settings['mongrel2_send_spec'], 
                        recv_spec=settings['mongrel2_recv_spec'])
    h.run(backend_sub_address=settings['pub_address'], 
          backend_push_address=settings['push_address'])
http_thread = Thread(target=http, name='http')

back_thread.start()
front_thread.start()
http_thread.start()
back_thread.join()
if front_thread.is_alive():
    front_thread.join()
if http_thread.is_alive():
    http_thread.join()
