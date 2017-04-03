from __future__ import absolute_import
from openearth.celery import app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@app.task()
def add2(x, y):
    logger.info('Adding %s + %s' % (x, y))
    return x + y


@app.task()
def tail_logfile(filepath, connection, channel, frequency=20.0):
    logger.info('Setting tail on: %s' % filepath)
    import time
    import subprocess
    import select
    f = subprocess.Popen(['tail', '-F', filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = select.poll()
    p.register(f.stdout)

    while True:
        if p.poll(1):
            subscribers = connection.publish(channel, f.stdout.readline())
        time.sleep(float(frequency) / 1000.0)


