# Start up a backend and two frontends: one for NetAcquire, one for HTTP 
# clients via Mongrel2.
# This script is meant to quickly get up and running, so I'm ok with the path 
# mangling going on here on a failed import.

import ConfigParser
import sys
from threading import Thread
try:
    import acquire
except ImportError:
    import os
    path_here = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.realpath(os.path.join(path_here, '../')))
    sys.path.insert(1, os.path.realpath(os.path.join(path_here, '../lib')))
from acquire.backend import Backend
from acquire.netacquire import NetAcquire

settings = {
    'pub_spec': 'tcp://127.0.0.1:16180',
    'push_spec': 'tcp://127.0.0.1:27183',
    'netacquire_address': '127.0.0.1:31415',
    'netacquire_name': 'Acquire',
    'mongrel2_sender_id': 'd693a7cc-2bba-469a-b478-11a50ca09116',
    'mongrel2_send_spec': 'tcp://127.0.0.1:9999',
    'mongrel2_recv_spec': 'tcp://127.0.0.1:9998',
}

config_path = "acquire.cfg" if len(sys.argv) <= 1 else sys.argv[1]
try:
    config = ConfigParser.RawConfigParser()
    config.read(config_path)
except ConfigParser.Error:
    config = None
if config and config.sections():
    for backend_setting in ['pub_spec', 'push_spec']:
        try:
            settings[backend_setting] = config.get('backend', backend_setting)
        except ConfigParser.NoOptionError:
            pass
        except ConfigParser.NoSectionError:
            break
    for netacquire_setting in ['address', 'name']:
        try:
            settings['netacquire_' + netacquire_setting] = config.get(
                'netacquire', netacquire_setting)
        except ConfigParser.NoOptionError:
            pass
        except ConfigParser.NoSectionError:
            del settings['netacquire_address']
            del settings['netacquire_name']
            break
    for mongrel2_setting in ['sender_id', 'send_spec', 'recv_spec']:
        try:
            settings['mongrel2_' + mongrel2_setting] = config.get('mongrel2', 
                                                            mongrel2_setting)
        except ConfigParser.NoOptionError:
            pass
        except ConfigParser.NoSectionError:
            del settings['mongrel2_sender_id']
            del settings['mongrel2_send_spec']
            del settings['mongrel2_recv_spec']
        break

back = Backend()
back_settings = {
    'pub_address': settings['pub_spec'],
    'pull_address': settings['push_spec'],
}
back_thread = Thread(target=back.run, name='backend', kwargs=back_settings)
front_thread = None
if 'netacquire_address' in settings:
    front = NetAcquire()
    accept_address = settings['netacquire_address'].split(':')
    accept_address = (accept_address[0], int(accept_address[1]))
    front_settings = {
        'server_name': settings['netacquire_name'],
        'backend_sub_address': settings['pub_spec'],
        'backend_push_address': settings['push_spec'],
        'accept_address': accept_address,
    }
    front_thread = Thread(target=front.run, name='netacquire', 
                          kwargs=front_settings)
http_thread = None
if 'mongrel2_send_spec' in settings:
    def http():
        from acquire.http import Mongrel2Handler
        h = Mongrel2Handler(settings['mongrel2_sender_id'], 
                            send_spec=settings['mongrel2_send_spec'], 
                            recv_spec=settings['mongrel2_recv_spec'])
        h.run(backend_sub_address=settings['pub_spec'], 
              backend_push_address=settings['push_spec'])
    http_thread = Thread(target=http, name='http')

back_thread.start()
if front_thread:
    front_thread.start()
if http_thread:
    http_thread.start()
back_thread.join()
if front_thread and front_thread.is_alive():
    front_thread.join()
if http_thread and http_thread.is_alive():
    http_thread.join()
