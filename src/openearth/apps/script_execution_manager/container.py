"""
CRUD-interface for LibVirt lxc containers
"""
from __future__ import unicode_literals
from django.conf import settings
from django.core.validators import validate_ipv46_address
from django.template import Context
from django.template.loader import get_template
import logging
# Get an instance of a logger
import os
import random
import shutil

import libvirt
import subprocess

logger = logging.getLogger(__name__)


class LibVirtDomainException(Exception):
    pass


def sizeof_fmt(num, use_kibibyte=True):
    base, infix = [(1000., ''), (1024., 'i')][use_kibibyte]
    for x in ['bytes', 'K%sB' % infix, 'M%sB' % infix, 'G%sB' % infix]:
        if num < base and num > -base:
            return "%3.1f%s" % (num, x)
        num /= base
    return "%3.1f %s" % (num, 'T%sB' % infix)


class LibVirtNet(object):
    """
    Manages defining and starting of network interfaces.

    This is class used to create the LibVirtDomain.network object.
    """

    def __init__(self, network_xml_template="containers/network.xml",
                 driver_uri="lxc:///", network_name="default",
                 vir_connect_obj=None):
        self.driver_uri = driver_uri
        self.template = get_template(network_xml_template)
        self.network_xml_template = get_template(network_xml_template)
        self.network_name = network_name
        if not vir_connect_obj:
            self.vir_connect_obj = libvirt.open(self.driver_uri)
        else:
            self.vir_connect_obj = vir_connect_obj

    def render_xml(self):
        """
        Renders the xml file, returns parsed xml
        """
        return self.template.render(Context({"name": self.network_name}))

    def define(self):
        """
        Define a network
        """
        xml = self.render_xml()
        return self.vir_connect_obj.networkDefineXML(xml)

    @property
    def network(self):
        return self.get_or_define()

    def get_or_define(self):
        """
        Returns existing network, or creates a new one
        """
        try:
            return self.vir_connect_obj.networkLookupByName(self.network_name)
        except libvirt.libvirtError:
            logger.info("Network '{0}' not found. Will define one.".format(
                self.network_name)
            )

        return self.define()

    def create(self):
        """
        Creates a network and returns it.
        """
        network = self.get_or_define()
        if not network.isActive():
            network.create()
        return network

    def destroy(self):
        """
        Destroys the network
        """
        if self.network.isActive():
            logger.info("Network was active; destroying required.")
            self.network.destroy()
        else:
            logger.warn("Network was not active; destroying not required. Undefining only.")
        self.network.undefine()


class LibVirtDomain(object):
    """
    Manages the creation of containers, from a template.

    For example:
    A minimal centos is installed in:
    /srv/{{app}}/containers/centos-6.5/

    On defining a domain this class parses a container.xml file; fills in the
    uuid, mount points, ram and vcpus. (TODO:.. and creates a new xml file from
    it. This file is copied to /srv/app/containers/instance-{UUID}.xml)
    When starting this domain; the minimal centos image is copied to
    /srv/{{app}}/containers/instance-{uuid}.

    When destroying a domain, this container image is removed.

    Example:
        lv = LibVirtDomain(uuid=uuid1(), image='centos-x86_64')
        lv.create()
        lv.destroy()
    """
    _network_mac_address = None
    dnsmasq_leases = '/var/lib/libvirt/dnsmasq/default.leases'
    _ip_address = None

    def __init__(self, uuid, image, domain_xml_template="containers/domain.xml",
                 driver_uri="lxc:///",
                 network_xml_template="containers/network.xml",
                 network_name="default", external_logger=None):
        """
        Checks template and initializes connection to LibVirtDomain.

        Arguments:
            uuid: unique identifier for the domain
            image: filename of image in dir settings.CONTAINER['base_dir']
            domain_xml_template: path to domain template.
            driver_uri: which driver is used and where (lxc, qemu,...)
            network: network name
            logger: logger object, which should be used for logging.

        """
        self.uuid = uuid
        self.image = image
        self.driver_uri = driver_uri
        self.results_dir = os.path.join(
            settings.CONTAINER['base_dir'],
            'results-{0}'.format(uuid)
        )
        self.template = get_template(domain_xml_template)
        self.vir_connect_obj = libvirt.open(self.driver_uri)
        self.network = LibVirtNet(
            network_xml_template=network_xml_template,
            driver_uri=driver_uri,
            network_name=network_name,
            vir_connect_obj=self.vir_connect_obj
        )
        if external_logger:
            self.configure_logger(external_logger)

    def configure_logger(self, external_logger):
        """
        Overwrites module logger handlers with new handlers.

        Used to add WebsocketLoggerHandler for example.

        Arguments:
            logger: a logger object
        """
        logger.handlers = external_logger.handlers

    @property
    def network_mac_address(self):
        """
        Generates a random mac address.

        This makes sure each container has its own ip address to connect to.
        """
        if not self._network_mac_address:
            mac = [
                0x00, 0x16, 0x3e,
                random.randint(0x00, 0x7f),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff)
            ]
            self._network_mac_address = ':'.join(map(lambda x: "%02x" % x, mac))

        return self._network_mac_address

    def get_instance_name(self):
        return "instance-{0}".format(self.uuid)

    def get_ip_address(self):
        """
        Matches mac address with ip leases from dnsmasq.

        This can only be run after creation of a VM. The default.leases file
        disappears after a while. Therefore it caches the current ip in
        self._ip_address

        Files:
            /var/lib/libvirt/dnsmasq/default.leases
        Sets:
            self._ip_address (str)
        Returns:
            ip address (str)
        """
        if self.domain.info()[0] != libvirt.VIR_DOMAIN_RUNNING:
            raise LibVirtDomainException(
                'Domain {0} not running. No ip address available.'.format(
                    self.get_instance_name()
                )
            )

        if not self._ip_address:
            with open(self.dnsmasq_leases, 'r') as fp:
                for line in fp:
                    mac = line.split(' ')[1]
                    ip = line.split(' ')[2]
                    if mac == self.network_mac_address:
                        validate_ipv46_address(ip)
                        return ip

            raise LibVirtDomainException(
                'No IP Address found for "{0}" with mac address "{1}".'.format(
                    self.get_instance_name(),
                    self.network_mac_address
                )
            )
        return self._ip_address

    def render_xml(self):
        """
        Renders the xml file, returns parsed xml
        """
        fs_params = {
            "base_dir": settings.CONTAINER['base_dir'],
            "instance_name": self.get_instance_name()
        }
        return self.template.render(Context({
            "name": self.get_instance_name(),
            "uuid": self.uuid,
            "network_mac_address": self.network_mac_address,
            "root_filesystem": "{base_dir}/{instance_name}".format(**fs_params),
            "results_filesystem": self.results_dir
        }))

    def define(self):
        """
        Defines a new domain
        """
        xml = self.render_xml()
        return self.vir_connect_obj.defineXML(xml)

    def copy_base_image(self):
        """
        Copies original read only image to run this instance on.
        """
        src = os.path.join(settings.CONTAINER['base_dir'], self.image)
        dst = os.path.join(
            settings.CONTAINER['base_dir'],
            self.get_instance_name()
        )
        if os.path.exists(dst):
            # Rewrite exception description to something humans understand
            raise LibVirtDomainException(
                'Instance image already exists: {0}'.format(dst)
            )

        logger.info("Copying image to '{0}'.".format(dst))
        length = 16*1024  # 10 times the blocksize as buffer

        try:
            with open(src, 'rb') as fsrc:
                # max_size defined by sparse file
                max_size = os.fstat(fsrc.fileno()).st_size

                # The actual size the sparse file uses on disk (check with du -sh)
                # http://bugs.python.org/file19108/shutil-2.7.patch for mor info
                actual_size = os.fstat(fsrc.fileno()).st_blocks * 512
                logger.info(
                    "Max size of image: {0} (already used: {1})".format(sizeof_fmt(max_size), sizeof_fmt(actual_size))
                )
                log_percent = 0
                with open(dst, 'wb') as fdst:
                    while 1:
                        current_size = os.fstat(fdst.fileno()).st_size
                        buf = fsrc.read(length)
                        if not buf:
                            break
                        if buf == '\0'*len(buf):
                            fdst.seek(len(buf), os.SEEK_CUR)  # this is the sparse / empty bit of a file
                        else:
                            fdst.write(buf)  # this buffer contains actual non sparse data, copy it to dst

                            percent = 100.0 * current_size/max_size
                            if percent >= 100.0:
                                logger.info("[# {:.1%} imgcopy info #] Copying image".format(100.0/100.0))
                            else:
                                if log_percent + 1 < percent:
                                    log_percent = percent
                                    logger.info("[# {:.1%} imgcopy info #] Copying image".format(percent/100.0))

                    fdst.truncate(max_size) # make this a sparse file like the originating file

            shutil.copystat(src, dst)
            logger.info("[# 100% imgcopy info #] Image copied")
        except OSError, e:
            logger.warn("Tried to copy image: {0}.".format(e))

        # shutil.copy2(
        #     os.path.join(settings.CONTAINER['base_dir'], self.image),
        #     target_path
        # )

    def create_results_dir(self):
        """
        Creates results-<uuid> dir in container base dir.
        """
        logger.info('Fixme: set results dir mode=0777 might not be a good idea...')
        try:
            os.makedirs(self.results_dir)
        except OSError:
            logger.warn(
                'Results dir already exists "{0}"'.format(self.results_dir)
            )
        os.chmod(self.results_dir, 0777)

    def delete_instance_image(self):
        """
        Deletes image of instance.
        """
        instance_image_path = os.path.join(
            settings.CONTAINER['base_dir'],
            self.get_instance_name()
        )
        try:
            os.remove(instance_image_path)
        except OSError:  # Raise helpful error message
            raise LibVirtDomainException("Trying to delete instance image '{0}', "
                          "but it does not exist.".format(instance_image_path))

    def delete_results_dir(self):
        shutil.rmtree(self.results_dir)

    @property
    def domain(self):
        """
        Not quite sure if this is the way to go. Defining a domain when it does
        not exist; perhaps hides too much on whats going on.
        - Return None?
        - Raise Exception?
        - Replace with: get_or_create_domain()?
        """
        return self.get_or_define()

    def get_or_define(self):
        """
        Defines a new domain; or gets it if it already exists.
        """
        try:
            return self.vir_connect_obj.lookupByName(self.get_instance_name())
        except libvirt.libvirtError:
            logger.info('Domain not found. Will define one.')
            pass

        return self.define()

    def create(self):
        """
        Copies image and creates (=runs) a domain (=container).
        """
        self.copy_base_image()
        self.network.create()
        self.create_results_dir()
        if self.domain.create() < 0:
            raise libvirt.libvirtError(
                'Cannot create domain: {0}'.format(self.get_instance_name())
            )
        logger.info('Created domain: {0}'.format(self.get_instance_name()))
        # self.get_ip_address() Was required for caching.
        # Does not work, because ip is not leased this fassed.

    def destroy(self):
        """
        Destroys (stop) and undefines domain. Deletes instance image.
        """
        self.delete_instance_image()
        try:
            self.domain.destroy()
        except libvirt.libvirtError:
            logger.warn("Tried to destroy '{0}', but it was not running.".format(self.get_instance_name()))
        self.domain.undefine()