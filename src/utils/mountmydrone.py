"""
This helps automate mounting your drone on Linux platforms, to make it ready
for BetaFlight
"""
import os
import sys
import re
import logging


logger = logging.getLogger(__name__)


PRODUCT_VENDER_REGEX = re.compile(r'[0-9a-z]{4}:[0-9a-z]{4}')
BETAFLIGHT_RESPONSE_CONNECT_SECONDS = 10


def lsusb():
    return os.popen('lsusb').read()


def modprobe_usb_product(vender, product):
    """
    Loads a module for vender and product
    """
    os.system('modprobe usbserial vender=%s product=%s' % (vender, product))


def usb_device_in_dmesg():
    """
    Finds the USB device in dmesg after calling modprobe_usb_product
    """
    dmesg_output = os.popen("sudo dmesg | grep 'USB' | grep 'tty'").read()
    tty_regex = re.compile(r'tty[A-Z]{,3}[0-9]:')
    usb_device = tty_regex.search(dmesg_output).group()
    usb_device = usb_device.rstrip(':') if usb_device else ""
    return usb_device
    

def correct_permissions(usb_device):
    """
    @device
        <str> 
    """
    os.system('chmod 777 %s' % usb_device)


def _update_truth_table(usb_data_one, usb_data_two, truth_table, attempt=0):
    """
    Checks if usb_device is in usb_data, and updates the truth_table
    
    @usb_data_one
        <str>
    
    @usb_data_two
        <str>
    
    @truth_table
        <dict>
    
    @attempt
        <int>
    
    @returns
        _update_truth_table with usb_data_one and usb_data_two switched 
        positions and stops when attempt > 1
    """
    if attempt > 1:
        return None
    
    for usb in usb_data_one:
        if usb in usb_data_two:
            truth_table[usb] = True
        else:
            truth_table[usb] = False

    return _update_truth_table(usb_data_two, usb_data_one, truth_table, attempt=attempt+1)


def diff_lsusb_output(usb_data_one, usb_data_two):
    """
    Finds the usb device that belongs to the drone
    
    @usb_data_one
        <str>
    
    @usb_data_two
        <str>
    
    @returns
        <tuple> (vender, product)
    """
    usb_data_one = usb_data_one.split('\n')
    usb_data_two = usb_data_two.split('\n')
    diff_table = {}
    _update_truth_table(usb_data_one, usb_data_two, diff_table)
    match = [PRODUCT_VENDER_REGEX.search(k).group() for k, v in diff_table.items() if v is False]
    if match:
        match = match[0]
        vender, product = match.split(':')
    else:
        vender, product = ("", "")
    return vender, product


def connect_usb_device():
    _ = input('Please disconnect drone from USB cable\nPRESS ENTER WHEN DONE\n')
    usb_dev_one = lsusb()
    _ = input('Please connect drone to USB\nPRESS ENTER WHEN DONE\n')
    usb_dev_two = lsusb()
    del _  # got rid of assigend but not used warning lol
    return usb_dev_one, usb_dev_two


def main():
    """
    Discovers the USB device for the drone, then loads the usbserial module, 
    and ensures the usb device has enough permissions for BetaFlight
    """
    if sys.platform not in ('linux', 'bsd'):
        sys.stderr.write('ERROR: Unsupported operating system')
        return None

    usb_devices_one, usb_devices_two = connect_usb_device()
    vender, product = diff_lsusb_output(usb_devices_one, usb_devices_two)
    if not vender or not product:
        sys.stderr.write('ERROR: Device not found. Let\'s try once again.\n')
        usb_devices_one, usb_devices_two = connect_usb_device()
        vender, product = diff_lsusb_output(usb_devices_one, usb_devices_two)
    if vender and product:
        try:
            dev_usb = '/dev/%s' % usb_device_in_dmesg()
            print("Loading module for usbserial (product=%s, vender=%s)" % (product, vender))
            modprobe_usb_product(vender, product)
            print('Setting permission to 777 on "%s"' % dev_usb)
            correct_permissions(dev_usb)
            success_msg = ('Successfully loaded USB module and ensured correct'
                           ' permissions for BetaFlight. It may take over 10'
                           ' seconds for BetaFlight to connect after mounting')
            print(success_msg)
            logger.info(success_msg)
        except PermissionError as permission_error:
            logger.exception(permission_error)
    else:
        sys.stderr.write('ERROR: Device not found. Check the cable and re-run')


if __name__ == "__main__":
    main()

    
        
    
    