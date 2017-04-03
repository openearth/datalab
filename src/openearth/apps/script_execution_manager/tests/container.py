from __future__ import unicode_literals
from django.core.validators import validate_ipv46_address
from django.conf import settings
from django.test import TestCase
import grp
import time
from uuid import uuid1
import libvirt
import logging
import os
import mock
import re
import xml.etree.ElementTree as ET
import shutil

from ..container import LibVirtDomain, LibVirtNet, LibVirtDomainException, logger as container_logger

logger = logging.getLogger(__name__)

states = {
    libvirt.VIR_DOMAIN_NOSTATE: 'no state',
    libvirt.VIR_DOMAIN_RUNNING: 'running',
    libvirt.VIR_DOMAIN_BLOCKED: 'blocked on resource',
    libvirt.VIR_DOMAIN_PAUSED: 'paused by user',
    libvirt.VIR_DOMAIN_SHUTDOWN: 'being shut down',
    libvirt.VIR_DOMAIN_SHUTOFF: 'shut off',
    libvirt.VIR_DOMAIN_CRASHED: 'crashed',
}


class LibVirtTestMixin(TestCase):
    """
    Shared methods for TestCases which make use of libvirt.
    """
    tmp_image_base_dir = '/tmp/containers'
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.dirname(__file__)
        cls.image_base_dir = os.path.join(cls.test_data_dir, 'data', 'containers')
        cls.config_tmp_image_dir(cls.image_base_dir, cls.tmp_image_base_dir)

    def tearDown(self):
        super(LibVirtTestMixin, self).tearDown()
        vir_connect_obj = libvirt.open("lxc:///")
        for net in vir_connect_obj.listAllNetworks():
            if net.isActive():
                print "Destroy network '{0}'".format(net.name())
                net.destroy()

            print "Undefine network '{0}'".format(net.name())
            net.undefine()

    @classmethod
    def tearDownClass(cls):
        """
        Removes copied instances and result dirs in /tmp/containers/.

        Directories and files are created by tests.
        /tmp/containers/results-<uuid> (dir)
        /tmp/containers/instance-<uuid>  (file)
        """
        re_image_name = re.compile(r"^instance-(.*)")
        re_result_dir = re.compile(r"^results-(.*)")
        if not os.path.exists(cls.tmp_image_base_dir):
            return
        
        for path in os.listdir(cls.tmp_image_base_dir):
            if re_image_name.match(path):
                logger.info('Cleaning instance image: {0} '.format(path))
                os.remove(os.path.join(cls.tmp_image_base_dir, path))
            if re_result_dir.match(path):
                logger.info('Cleaning results dir: {0} '.format(path))
                shutil.rmtree(os.path.join(cls.tmp_image_base_dir, path))

    def patch_lv_obj(self, lv):
        """
        Fixes things like leases file and mac address.
        """
        lv.dnsmasq_leases = os.path.join(self.test_data_dir, 'data', 'default.leases')
        lv._network_mac_address = "00:16:3e:46:ae:51"
        return lv

    @classmethod
    def config_tmp_image_dir(cls, image_base_dir, tmp_image_base_dir):
        """
        Configure /tmp/containers/ with image. Required because that dir is
        writable.

        TODO: share me with tests/container.py Make ContainerTest inheritance
        class.
        """
        image_src = os.path.join(image_base_dir, 'base_image')
        if not os.path.exists(tmp_image_base_dir):
            os.makedirs(tmp_image_base_dir)

        shutil.copy2(
            image_src,
            tmp_image_base_dir
        )


class LibVirtTest(LibVirtTestMixin):
    # Bogus domain state running, in format of domain.info()
    domain_state_running = [libvirt.VIR_DOMAIN_RUNNING, 524288L, 28996L, 1, 695391255L]

    def test_init_ok_no_uri(self):
        self.assertIsInstance(
            LibVirtDomain(uuid=uuid1(), image='base_image'), LibVirtDomain
        )

    def test_init_ok_with_uri(self):
        self.assertIsInstance(
            LibVirtDomain(uuid=uuid1(), image='base_image', driver_uri='lxc:///'),
            LibVirtDomain
        )

    def test_init_fails_on_wrong_driver_uri(self):
        self.assertRaises(
            libvirt.libvirtError,
            LibVirtDomain,
            uuid=uuid1(),
            image='base_image',
            driver_uri='bla:///'
        )

    def test_configure_logger(self):
        """
        Test if logger handler is added to the list of loggers.
        """
        handler = logging.NullHandler()
        test_logger = logging.getLogger('test_configure_logger')
        test_logger.addHandler(handler)
        LibVirtDomain(
            uuid=uuid1(),
            image='base_image',
            external_logger=test_logger
        )
        self.assertIn(handler, container_logger.handlers)
        test_logger.handlers = []
        test_logger = logging.getLogger('test_configure_logger')
        test_logger.addHandler(handler)
        LibVirtDomain(
            uuid=uuid1(),
            image='base_image',
            external_logger=test_logger
        )
        self.assertIn(handler, container_logger.handlers)
        self.assertEqual(1, len(container_logger.handlers))

    # def test_add_logger_handler(self):
    #     """
    #     Test if logger handler is added to the list of loggers.
    #     """
    #     handler = logging.NullHandler()
    #     LibVirtDomain(
    #         uuid=uuid1(),
    #         image='base_image',
    #         extra_logger_handlers=[handler]
    #     )
    #     self.assertIn(handler, container_logger.handlers)

    def test_generate_mac_address(self):
        """
        Tests if a mac address is generated and matches a regex.
        """
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
        self.assertRegexpMatches(
            lv.network_mac_address,
            re.compile("^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$", re.IGNORECASE)
        )

    def test_get_ip_address_domain_not_running_raises_exception(self):
        #1393849324 00:16:3e:46:ae:51 192.168.122.246 * *
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
        self.assertRaisesRegexp(
            LibVirtDomainException,
            "Domain instance-(.*) not running. No ip address available",
            lv.get_ip_address
        )

    @mock.patch(
        'libvirt.virDomain.info',
        new=lambda x: LibVirtTest.domain_state_running
    )
    def test_get_ip_address_none_available(self):
        #1393849324 00:16:3e:46:ae:51 192.168.122.246 * *
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
        lv.dnsmasq_leases = os.path.join(self.test_data_dir, 'data', 'default.leases')
        self.assertRaisesRegexp(
            LibVirtDomainException,
            r'No IP Address found for "instance-.*',
            lv.get_ip_address
        )

    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_get_ip_address(self):
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
        lv.dnsmasq_leases = os.path.join(self.test_data_dir, 'data', 'default.leases')
        lv._network_mac_address = "00:16:3e:46:ae:51"
        validate_ipv46_address(lv.get_ip_address())

    def test_render_xml(self):
        """
        Test if the rendered xml contains all expected elements and attributes.

        Correct elements for:
          - base image
          - results filesystem
          - network mac address
        """
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
        xml = lv.render_xml()
        root = ET.fromstring(xml)
        # Test name, uuid
        xuuid = root.findall('./uuid')
        self.assertEqual(len(xuuid), 1)
        self.assertEqual(
            xuuid[0].text,
            unicode(uuid)
        )
        xname = root.findall('./name')
        self.assertEqual(
            xname[0].text,
            'instance-{0}'.format(uuid)
        )
        # Test filesystem
        xfsdir = root.findall(
            './devices/filesystem/source'
            '[@file="{root_fs}/instance-{uuid}"]'.format(**{
                "root_fs": settings.CONTAINER['base_dir'],
                "uuid": uuid
            })
        )
        self.assertEqual(len(xfsdir), 1, "No correct root filesystem defined")
        xresults_dir = root.findall(
            './devices/filesystem/source'
            '[@dir="{root_fs}/results-{uuid}"]'.format(**{
                "root_fs": settings.CONTAINER['base_dir'],
                "uuid": uuid
            })
        )
        self.assertEqual(len(xresults_dir), 1, "No correct results filesystem defined")
        # Test network
        xifnetwork = root.findall(
            './devices/interface/source[@network="default"]'
        )
        self.assertEqual(len(xifnetwork), 1, "No correct network defined")

        xnetworkmac = root.findall(
            './devices/interface/mac'
        )
        self.assertEqual(
            xnetworkmac[0].attrib['address'],
            lv.network_mac_address,
            "Mac addres undefined or incorrect"
        )

    def test_get_or_create_domain_defined_returned(self):
        """
        Tests if a domain is defined and returned
        """
        lv = LibVirtDomain(uuid=uuid1(), image='base_image')
        self.assertIsInstance(lv.get_or_define(), libvirt.virDomain)

    def test_get_or_create_domain_existing_returned(self):
        """
        Tests if a domain which already exists is returned
        """
        uuid = uuid1()
        lv = LibVirtDomain(uuid=uuid, image='base_image')
        self.assertIsInstance(lv.get_or_define(), libvirt.virDomain)
        lv2 = LibVirtDomain(uuid=uuid, image='base_image')
        self.assertEqual(
            lv.domain.name(),
            lv2.domain.name()
        )

    def test_copy_base_image(self):
        """
        Copies base bogus image to /tmp. Tests links, dirs and files.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }

        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid1(), image='base_image')
            lv.copy_base_image()

        image = os.path.join(self.tmp_image_base_dir, lv.get_instance_name())
        self.assertTrue(
            os.path.isfile(os.path.join(image)),
            '{0} is not a file'.format(os.path.join(image))
        )

    def test_create_results_dir(self):
        """
        Tests if /data/containers/results-uuid is created and has correct mode.

        # todo; write in tmp. clean afterwards.
        """
        uuid = uuid1()
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
            self.assertIsNone(lv.create_results_dir())
            results_dir = os.path.join(
                settings.CONTAINER['base_dir'],
                'results-{0}'.format(uuid)
            )
            self.assertEqual((os.stat(results_dir).st_mode & 0777), 0777)

    def test_create_results_dir_twice(self):
        """
        Tests if creating a dir twice does not matter.
        """
        uuid = uuid1()
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
            self.assertIsNone(lv.create_results_dir())
            results_dir = os.path.join(
                settings.CONTAINER['base_dir'],
                'results-{0}'.format(uuid)
            )
            self.assertEqual((os.stat(results_dir).st_mode & 0777), 0777)

            lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
            self.assertIsNone(lv.create_results_dir())
            results_dir = os.path.join(
                settings.CONTAINER['base_dir'],
                'results-{0}'.format(uuid)
            )
            self.assertEqual((os.stat(results_dir).st_mode & 0777), 0777)

    def test_delete_results_dir(self):
        """
        Tests if /data/containers/results-uuid is created

        # kan dat met unittest permissies?
        """
        uuid = uuid1()
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid, image='base_image', driver_uri='lxc:///')
            self.assertIsNone(lv.create_results_dir())
            self.assertIsNone(lv.delete_results_dir())


    def test_copy_base_image_path_exists(self):
        """
        Copies base bogus image to /tmp. Tests links, dirs and files.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid1(), image='base_image')
            lv.copy_base_image()
            self.assertRaisesRegexp(
                LibVirtDomainException,
                r"Instance image"
                r" already exists:.*",
                lv.copy_base_image
            )

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_create_domain(self):
        """
        Tests if creating (starting) a domain works.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid1(), image='base_image')
            lv = self.patch_lv_obj(lv)
            self.assertIsNone(lv.create())

    @mock.patch('libvirt.virDomain.create', new=lambda x: -1)
    def test_create_domain_fails_when_domain_exists(self):
        """
        Tests if creating (starting) a domain fails when create() fails.

        Sometimes a domain is not created, returns -1, but raises no exception.
        Check if custom exception is raised.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
            'base_image': 'base_image'
        }
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid1(), image='base_image', network_name="test_network"
            )
            self.assertRaisesRegexp(
                libvirt.libvirtError,
                r'Cannot create domain: .*',
                lv.create
            )

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    def test_domain_has_network(self):
        """
        Tests if creating (starting) a domain works.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir
        }
        network_name = "test_network"
        uuid = uuid1()
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid, image='base_image', network_name=network_name
            )
            self.assertIsInstance(lv.network, LibVirtNet)
            network = lv.network.get_or_define()
            self.assertEqual(network.name(), network_name)

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_delete_instance_image(self):
        """
        Test if image file is deleted.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        network_name = "test_network"
        uuid = uuid1()
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid, network_name=network_name, image='base_image'
            )
            lv = self.patch_lv_obj(lv)
            lv.create()
            lv.delete_instance_image()
            instance_path = os.path.join(
                container_settings['base_dir'],
                lv.get_instance_name()
            )
            self.assertFalse(os.path.exists(instance_path))

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_delete_instance_image_fails_when_no_image(self):
        """
        Test if correct exception and message are raised when deleting fails.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
        }
        network_name = "test_network"
        uuid = uuid1()
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid, network_name=network_name, image='base_image'
            )
            lv = self.patch_lv_obj(lv)
            lv.create()
            instance_path = os.path.join(
                container_settings['base_dir'],
                lv.get_instance_name()
            )
            os.remove(instance_path)
            self.assertRaisesRegexp(
                LibVirtDomainException,
                "Trying to delete instance image '.*', but it does not exist",
                lv.delete_instance_image
            )

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.destroy', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.isActive', new=lambda x: 0)
    @mock.patch('libvirt.virDomain.info', new=lambda x: LibVirtTest.domain_state_running)
    def test_destroy_domain(self):
        """
        Test if image is deleted, domain is destroyed and undefined.
        """
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
            'base_image': 'base_image'
        }
        network_name = "test_network"
        uuid = uuid1()
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(
                uuid=uuid, image='base_image', network_name=network_name
            )
            lv = self.patch_lv_obj(lv)
            instance_path = os.path.join(
                container_settings['base_dir'],
                lv.get_instance_name()
            )
            instance_name = lv.get_instance_name()
            lv.create()
            lv.destroy()
            domain = lv.domain
            self.assertFalse(os.path.exists(instance_path))
            vir_connect_obj = libvirt.open('lxc:///')
            self.assertEqual(domain.isActive(), 0)


class LibVirtNetworkTest(LibVirtTestMixin):

    def test_render_xml(self):
        """
        Tests if render_xml returns xml

        Also checks if elements contain expected data.
        """
        lvn = LibVirtNet()
        xml = lvn.render_xml()
        root = ET.fromstring(xml)
        # Test name, uuid
        xmame = root.findall('./name')
        self.assertEqual(len(xmame), 1)
        self.assertEqual(
            xmame[0].text,
            "default"
        )

    def test_define(self):
        network_name = "test_network"
        lvn = LibVirtNet(network_name=network_name)
        network = lvn.define()
        self.assertIsInstance(network, libvirt.virNetwork)
        self.assertEqual(network.name(), network_name)

    def test_get_or_define(self):
        network_name = "test_network"
        lvn = LibVirtNet(network_name=network_name)
        # Define network
        network = lvn.get_or_define()
        # This shold get the existing network
        network_existing = lvn.get_or_define()
        self.assertEqual(network.UUIDString(), network_existing.UUIDString())

    def test_create(self):
        network_name = "test_network"
        lvn = LibVirtNet(network_name=network_name)
        network = lvn.create()
        self.assertIsInstance(network, libvirt.virNetwork)
        self.assertEqual(network.name(), network_name)


    # This should not fail! Test is wrong.
    # def test_create_double_fails(self):
    #     """
    #     Test if creating a network twice from the same LibVirtNet object fails
    #     """
    #     network_name = "test_network"
    #     lvn = LibVirtNet(network_name=network_name)
    #     network = lvn.create()
    #     self.assertRaisesRegexp(
    #         libvirt.libvirtError,
    #         r"operation failed: network '.*' already exists with uuid .*",
    #         lvn.create
    #     )
    #
    # def test_create_double_on_two_objects_fails(self):
    #     """
    #     Test if creating 2 objects with same name fails.
    #     """
    #     network_name = "test_network"
    #     lvn = LibVirtNet(network_name=network_name)
    #     lvn.create()
    #
    #     # Second network with same name
    #     lvn2 = LibVirtNet(network_name=network_name)
    #     self.assertRaisesRegexp(
    #         libvirt.libvirtError,
    #         r"operation failed: network '.*' already exists with uuid .*",
    #         lvn2.create
    #     )

    def test_destroy(self):
        network_name = "test_network"
        lvn = LibVirtNet(network_name=network_name)
        network = lvn.define()
        self.assertIsInstance(network, libvirt.virNetwork)
        self.assertEqual(network.name(), network_name)
        lvn.destroy()
        vir_connect_obj = libvirt.open("lxc:///")
        self.assertRaisesRegexp(
            libvirt.libvirtError,
            r"Network not found: no network with matching name 'test_network'",
            vir_connect_obj.networkLookupByName,
            network_name
        )

    @mock.patch('libvirt.virDomain.create', new=lambda x: 0)
    def test_destroy_when_active(self):
        """
        Tests if destroying a network which is active, works.
        """
        test_data_dir = os.path.dirname(__file__)
        self.image_base_dir = os.path.join(test_data_dir, 'data', 'containers')
        container_settings = {
            'base_dir': self.tmp_image_base_dir,
            #'base_image': 'base_image'
        }
        network_name = 'test_network'
        with self.settings(CONTAINER=container_settings):
            lv = LibVirtDomain(uuid=uuid1(), image='base_image', network_name=network_name)
            self.assertIsNone(lv.create())
            # Make sure it's active
            self.assertEqual(
                lv.network.network.isActive(),
                1
            )
            lv.network.destroy()
            # Make sure it's inactive
            self.assertEqual(
                lv.network.network.isActive(),
                0
            )
