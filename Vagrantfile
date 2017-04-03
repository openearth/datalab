# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'pp'

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    config.vm.hostname = '198.51.100.3'
    config.vm.network :private_network, ip: "198.51.100.3"
    config.vm.network :forwarded_port, guest: 22, host: 2223, auto_correct: true
    config.vm.network :forwarded_port, guest: 80, host: 8001, auto_correct: true
    config.vm.network :forwarded_port, guest: 443, host: 8443, auto_correct: true
    config.vm.network :forwarded_port, guest: 8000, host: 8000, auto_correct: true
    config.vm.network :forwarded_port, guest: 8080, host: 8080, auto_correct: true

    config.vm.synced_folder "src/", "/srv/openearth/src/",
        id: "src", :mount_options => ["uid=500,gid=500"]

    config.vm.provider :virtualbox do |vb|

    path_1 = File.expand_path("~/Virtual Machines")
    path_2 = File.expand_path("~/VirtualBox VMs")
    if File.directory?(path_1)
      disk_path = path_1
    elsif File.directory?(path_2)
      disk_path = path_2
    else
      raise "Create a ~/Virtual Machines or ~/VirtualBox VMs directory."
    end

    disk_path << "/openearth_disk_data.vmdk"

    # Use VBoxManage to customize the VM. For example to change memory:
    config.vm.provider "virtualbox" do |vb|
      vb.memory = 2048
      vb.cpus = 2
    end

    # Add extra filesystem: https://gist.github.com/leifg/4713995
    unless File.exists?(disk_path)
        puts "Creating HD"
        vb.customize ['createhd', '--filename', disk_path, '--size', 20 * 1024, "--format", "vmdk"]
    end
    vb.customize ['storageattach', :id, '--storagectl', 'IDE Controller', '--port', 1, '--device', 0, '--type', 'hdd', '--medium', disk_path]
  end

  #config.vbguest.auto_update = true

  config.vm.define "default", primary: true do |default|
    default.vm.box = "centos-6.5-x86_64"
    default.vm.box_url = "http://puppet-vagrant-boxes.puppetlabs.com/centos-65-x64-virtualbox-nocm.box"

    default.vm.provision :ansible do |ansible|
      ansible.playbook = "provisioning/site.yml"
      ansible.inventory_path = "provisioning/inventory_otap"
      ansible.limit = "development"
      ansible.verbose = "vvvv"
      ansible.skip_tags = "python_container,matlab_container"
      ansible.extra_vars = {
        remove_python_container: "N",
        remove_matlab_container: "N"
      }
    end
  end

  if File.exists?('Vagrantfile.local')
    external = File.read 'Vagrantfile.local'
    eval external # this should overwrite proxy config
  end
end
