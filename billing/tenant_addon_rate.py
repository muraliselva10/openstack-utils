#!/usr/bin/env python                                                                                                                                                                                      
#                                                                                                                                                                                                          
# tenant addon rating script
# get for the available tenant addon ratings
# check if the tenant addon rating is already added
# Add rating frames if tenant is not rated for current month
# Script should be set to run each and everyday
#
# Author: Muralidharan.S
#

from cloudkittyclient import client
from cloudkittyclient.common import utils
from novaclient import client as nova_client
from keystoneclient.v2_0 import client as kclient
from keystoneclient.auth.identity import v3
from keystoneclient import session
from collections import defaultdict
import ConfigParser
import datetime
import logging
import json
import dateutil.relativedelta
import simplejson as json
import pytz
import time
from dateutil import tz
import calendar
from cloudkitty import utils as ck_utils

# For importing details from config file
config = ConfigParser.RawConfigParser()
config.read('/etc/cloudkitty/cloudkitty.conf')

# Fetch details from config file
# For connection part
connection = dict(config.items("keystone_fetcher"))
extra_config = dict(config.items("extra_conf"))

# kwargs for connection
kwargs_conn = {
    "tenant_name":connection['username'],
    "auth_url":connection['auth_url'],
    "username":connection['username'],
    "password":connection['password'],
    "nova_version": extra_config['nova_version'],
    "cloudkitty_version": extra_config['cloudkitty_version'],
    "log_file": extra_config['log_file'],
    "region_name": connection['region']
}

# keystone client establish connection
keystone = kclient.Client(**kwargs_conn)

# Establish the connection Cloudkitty
ck = client.get_client(kwargs_conn.get('cloudkitty_version'), **kwargs_conn)

# get todays date
today_date = datetime.datetime.today()

# can edit date for debugging and verification
# today_date = today_date.replace(day=01, month=06, year=2016, hour=00, minute=00, second=00, microsecond=0)

# Take current month and year
month = today_date.month
year = today_date.year

# set the begin period
begin_period = today_date.replace(day=1, 
                                  hour=0, 
                                  minute=0,
                                  second=0, 
                                  microsecond=0)

# set the end period
end_date_period = calendar.monthrange(year, month)[1]
end_period = today_date.replace(day=end_date_period, 
                                hour=23, 
                                minute=59, 
                                second=59, 
                                microsecond=0)

# take the services list
list_services = ck.hashmap.services.list()

# getting the relevant service id
for services in list_services:

    # getting the service id for tenant.addon
    if services.name == 'tenant.addon':
        service_id = services.service_id

# get the relevant fields for the service
list_fields = ck.hashmap.fields.list(service_id=service_id)

for fields in list_fields:

    if fields.name == 'tenant_id':
        field_id = fields.field_id

# mappings available for particular field
# getting the tenants needs to rated
list_mappings = ck.hashmap.mappings.list(field_id=field_id)

# for available tenant addons
for mappings in list_mappings:

    mapping_details = mappings
    tenant_id = mapping_details.value

    # get the available rated dataframes for tenant.addon
    list_rated_frames = ck.storage.dataframes.list(resource_type='tenant.addon', 
                                                   begin=begin_period, 
                                                   end=end_period, 
                                                   tenant_id=tenant_id)

    # frame count to decide the course of action
    frames_count = len(list_rated_frames)

    # for adding necessary details
    rate = mapping_details.cost

    # get the tenant details
    try:

        tenant =  keystone.tenants.get(tenant_id)
        dicts = {'name': tenant.name, 'description': tenant.description, 
                 'tenant_id': tenant_id, 'creation_time': tenant.creation_date, 
                 'timezone': tenant.timezone}

    except:

        dicts = {'tenant_id': tenant_id}

    # if tenant addon is not rated for this month
    if frames_count == 0:

        # add dataframes
        add_rated_frames = ck.storage.dataframes.create(res_type='tenant.addon',
                                                        begin=ck_utils.dt2iso(begin_period),
                                                        end=ck_utils.dt2iso(begin_period),
                                                        tenant_id=tenant_id,
                                                        unit='tenant', 
                                                        qty='1', 
                                                        rate=rate, 
                                                        desc=dicts)
