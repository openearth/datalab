from __future__ import unicode_literals
import logging
from django.test import TestCase
import os
from ..exec_wrapper import ExecWrapper, mark_secret, SecretString


logger = logging.getLogger(__name__)


class ExecWrapperTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.test_script = os.path.join(cls.test_data_dir, 'stdout_stderr.sh')

    def test_start_process(self):
        """
        Tests if process return code is given and process yielded lines
        """
        ew = ExecWrapper(command=['sh', self.test_script, '--password', mark_secret('secret')])
        lines = []
        for l in ew.start_process():
            lines.append(l)

        self.assertGreater(len(lines), 0)
        self.assertEqual(ew.get_return_code(), 0)

    def test_command_succeeds(self):
        """
        Tests if a command with exit code 0 returns exit code.
        """
        ew = ExecWrapper(
            command=['/usr/bin/uptime'],
        )
        for l in ew.start_process():
            print l
        self.assertEqual(ew.get_return_code(), 0)

    def test_command_fails(self):
        """
        Tests if a command with exit code > 0 raises exception.
        """
        ew = ExecWrapper(
            command=['/usr/bin/svn', 'blaat'],
        )
        generator = ew.start_process()
        self.assertRaisesRegexp(
            Exception,
            r"Command '/usr/bin/svn blaat' failed",
            lambda: list(generator)
        )

    def test_parse_command(self):
        secret = 'a secret pass'
        ew = ExecWrapper(
            command=['/usr/bin/svn', '--password', mark_secret(secret)],
        )
        parsed_command = ew.parse_command()
        self.assertEqual(parsed_command[2], secret)


class ExecWrapperUtilsTest(TestCase):

    def test_mark_secret(self):
        """
        Test if string is of type SecretString.
        """
        secret = 'replace me with XXXXXX'
        formatted_secret = mark_secret(secret)
        self.assertIsInstance(formatted_secret, SecretString)
        self.assertEqual('XXXXXXXX', formatted_secret)
        self.assertEqual(secret, formatted_secret.get_secret())

    def test_mark_secret_2(self):
        secret = 'asdasd'
        formatted_secret = SecretString(secret)
        self.assertIsInstance(formatted_secret, SecretString)
        self.assertEqual('XXXXXXXX', formatted_secret)
        self.assertEqual(secret, formatted_secret.get_secret())




