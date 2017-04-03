"""
Executes a command, redirects stderr and stdout to a file and to redis.
"""
import logging
import subprocess
import select

logger = logging.getLogger(__name__)


class ExecWrapper(object):

    def __init__(self, command):
        """
        Execute a command, start_process() yields stderr and stdout.

        Args:
            command: String or List for subprocess.popen(command)

        Example:
            ExecWrapper(['python', '-u', 'bla.py'])
        """
        self.command = command
        self.process = None

    def parse_command(self):
        """
        Process command list, get secrets from any SecretString list items.

        Returns:
            list of command, with secrets written out.
        Example:
            This: ['/usr/bin/svn', '--password', 'XXXXXXX']
            Becomes: ['/usr/bin/svn', '--password', 'The hidden password']
        """
        def get_secret(c):
            return c.get_secret() if hasattr(c, 'get_secret') else c

        return map(get_secret, self.command)

    def start_process(self):
        """
        Starts a process and catches stderr and stdout. yields it.

        Returns:
            The return code of the executed command.
        """
        self.process = subprocess.Popen(
            self.parse_command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        epoll = select.epoll()
        fds = {
            self.process.stdout.fileno(): self.process.stdout,
            self.process.stderr.fileno(): self.process.stderr,
        }

        for fd in fds.itervalues():
            epoll.register(fd.fileno())

        while fds:
            events = epoll.poll(1, select.EPOLLIN)
            #events = epoll.poll(1)
            for fileno, event in events:
                if event & select.EPOLLIN:
                    yield fds[fileno].readline()
                elif event & select.EPOLLHUP:
                    logger.debug("EPOLLHUP for '{0}' on fileno {1}".format(
                        ' '.join(self.command),
                        fileno
                    ))
                    epoll.unregister(fileno)
                    del fds[fileno]
        self.process.wait()
        logger.debug("Process '{0}' ended with return code '{1}'".format(
            ' '.join(self.command),
            self.process.returncode
        ))

        if self.process.returncode > 0:
            msg = "Command '{0}' failed".format(' '.join(self.command))
            raise Exception(msg)

    def get_return_code(self):
        return self.process.returncode


class SecretString(unicode):
    """
    Printing will display XXXXXXXX. Use get_secret() method to get secret value.

    Example:
        >>> formatted_secret = mark_secret('replace me with XXXXXX')
        >>> print formatted_secret
        >>> 'XXXXXXXX'
        >>> print formatted_secret.get_secret()
        >>> 'replace me with XXXXXX'

    """
    def __new__(cls, value, *args, **kwargs):
        return unicode.__new__(cls, u'XXXXXXXX')

    def __init__(self, value):
        self.secret_value = value

    def get_secret(self):
        return self.secret_value


def mark_secret(input):
    """
    Makes a string SecretString. ExecWrapper logs the value as XXXXXXXX.

    mark_secret is inspired on Django's mark_safe; therefore this function is
    used to make the str input a SecretString object.

    Arguments:
        input, a string.
    """
    return SecretString(input)

