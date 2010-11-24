# Start up a backend and a NetAcquire frontend.

from threading import Thread
from acquire.backend import Backend
from acquire.netacquire import NetAcquire

settings = {
    'pub_address': 'tcp://127.0.0.1:16180',
    'push_address': 'tcp://127.0.0.1:27183',
    'netacquire_address': '127.0.0.1:31415',
    'netacquire_name': 'Acquire',
}

back = Backend()
back_settings = {
    'pub_address': settings['pub_address'],
    'pull_address': settings['push_address'],
}
back_thread = Thread(target=back.run, kwargs=back_settings)
front = NetAcquire()
accept_address = settings['netacquire_address'].split(':')
accept_address = (accept_address[0], int(accept_address[1]))
front_settings = {
    'server_name': settings['netacquire_name'],
    'backend_sub_address': settings['pub_address'],
    'backend_push_address': settings['push_address'],
    'accept_address': accept_address,
}
front_thread = Thread(target=front.run, kwargs=front_settings)

back_thread.start()
front_thread.start()
back_thread.join()
if front_thread.is_alive():
    front_thread.join()
