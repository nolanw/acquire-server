Let's play Acquire again!
=========================

It's been awhile since good old [NetAcquire](http://www3.telus.net/kensit/NetAcquire/) had a server up and running. I think part of the reason is that it was Windows only, and part of that reason is that it was hard to keep running.

**acquire-server** changes that.


How to run
----------

  1. [Install 0mq if needed.](http://www.zeromq.org/intro:get-the-software)
  2. [Install the Python bindings for 0mq if needed.](http://www.zeromq.org/bindings:python)
  3. Check this repository out.
  4. Add its root to your `PYTHONPATH` (e.g. `export PYTHONPATH="~/code/acquire:$PYTHONPATH"`).
  5. Fire it up: `python acquire/run.py`
  6. Connect to `localhost` port `31415` with NetAcquire or [Acquire.app](http://nolanw.ca/acquire).
