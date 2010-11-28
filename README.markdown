Let's play Acquire again!
=========================

It's been awhile since good old [NetAcquire](http://www3.telus.net/kensit/NetAcquire/) had a server up and running. I think part of the reason is that it was Windows only, and part of that reason is that it was hard to keep running.

**acquire-server** changes that.


All kinds of clients
--------------------

I also want to make other clients, like a browser client. The beginnings of a Mongrel2 handler and an example of how to use it are included.


How to run
----------

  1. [Install 0mq if needed.](http://www.zeromq.org/intro:get-the-software)
  2. [Install the Python bindings for 0mq if needed.](http://www.zeromq.org/bindings:python)
  3. Check this repository out.
  4. Fire it up: `python acquire/run.py`
  5. Connect to `localhost` port `31415` with NetAcquire or [Acquire.app](http://nolanw.ca/acquire).


See also
--------

Check the examples directory for how to set up the Mongrel2 handler to get acquire-server to talk over HTTP.
