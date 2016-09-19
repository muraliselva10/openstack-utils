#!/usr/bin/env python
#
# Billing script
# Automated billing script for all tenants
# Will Add the invoice details details for tenants
# During the run it will check for creation date of tenant
# If creation day and current day is same
# Invoice will be generated to tenant
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

# Establish the connection NOVA
nt = nova_client.Client(kwargs_conn.get('nova_version'), kwargs_conn.get('username'), kwargs_conn.get('password'), kwargs_conn.get('tenant_name'), kwargs_conn.get('auth_url'))

# Logging the items
# Log Definition
logging.basicConfig(filename=kwargs_conn.get('log_file'), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

# current date operations
mylist = []
today = datetime.datetime.today()
mylist.append(today)
date = mylist[0]

# for debugging you can assume date here
#date = date.replace(day=15, month=06, year=2016, hour=22, minute=47, second=59, microsecond=0)
print date

# Billing engine class
# let us create bill for tenants
class BillingEngine():

    # Execution starts here
    # Getting the tenant list
    # Fetch the creation_date of tenant if exists
    def run(self):

        # Fetch tenant list
        tenants_list = keystone.tenants.list()

        # for each tenants in list
        for tenant in tenants_list:

            # fetch tenant id
            tenant_id = tenant.id

            # creation date for tenant
            creation_date = tenant.__dict__.get("creation_date", None)
          
            # if creation_date exists 
            if creation_date is not None: 

                    # Format creation date
                    creation_date = datetime.datetime.strptime(creation_date, '%Y-%m-%d %H:%M:%S')

                    # replacing the creation_date of tenant 
                    # which have unclear creation date      
                    if creation_date.day in (29, 30, 31):

                        logging.info("Assuming creation date for tenant %s having unclear creation date" % (creation_date))
                        creation_date = creation_date.replace(day=28)

                        # start with date check operations
                        self.date_check(creation_date, tenant_id, date)

                    # tenant have clear creation date
                    else:

                        # start with date check operations
                        self.date_check(creation_date, tenant_id, date)

            # else section for no creation date exists
            else:
                logging.info("Creation date not exists for client")

    def date_process(self, tenant_id, creation_date, date):
        
        logging.info("Creation date of tenant %s is today %s, Gonna check invoice_details table for next step" % (tenant_id, creation_date))
    
        # Get the invoice using Cloudkitty client
        invoice = ck.reports.get_invoice(tenant_id=tenant_id)
    
        # dict for storing dates
        invoice_date_list = defaultdict(list)
    
        # if invoice exists
        # that is not first run
        if invoice:
    
            # for storing items in dict
            for items in invoice:
    
                # take date from invoice dict
                invoice_date = items.invoice_date
    
                # append invoice dates
                invoice_date_list[tenant_id].append(invoice_date)
                invoice_date_for_tenant = invoice_date_list.get(tenant_id, None)
    
            # to find latest invoice date
            invoice_date_latest = max(invoice_date_for_tenant)
            invoice_date_latest = datetime.datetime.strptime(invoice_date_latest, '%Y-%m-%dT%H:%M:%SZ')
    
            # naive object
            invoice_date_latest = invoice_date_latest.replace(tzinfo=None)
    
            # Calculate diff
            diff = date - invoice_date_latest

            # Diff in days
            days_diff = diff.days
    
            # If diff is greater than 28 days
            if days_diff > 28:
    
                logging.info("Tenant %s is elligible for next invoice creation" % (tenant_id))
    
                # begin date and end date set
                begin = date - dateutil.relativedelta.relativedelta(months=1)
                end = date - dateutil.relativedelta.relativedelta(days=1)
          
                begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
                end = end.replace(hour=23, minute=59, second=59, microsecond=0)

                local_begin = begin
                local_end = end

                begin = self.local2utc(dt=begin)
                end = self.local2utc(dt=end)

                logging.info("Assuming the invoice from period in UTC (%s) instead of local time (%s)" % (begin, local_begin))
                logging.info("Assuming the invoice TO period in UTC (%s) instead of local time (%s)" % (end, local_end))

                # call the function for creation of invoice
                self.calc_and_create(tenant_id, begin, end, local_begin, local_end, date)
    
            # Logging the details for already created invoice
            else:
    
                logging.info("Invoice already created for this period - Tenant id %s" % (tenant_id))
    
        # if it is first run
        else:
    
            logging.info("Tenant %s's first invoice creation" % (tenant_id))
    
            # begin date and end date set
            begin = date - dateutil.relativedelta.relativedelta(months=1)
            end = date - dateutil.relativedelta.relativedelta(days=1)

            begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
            end = end.replace(hour=23, minute=59, second=59, microsecond=0)

            local_begin = begin
            local_end = end

            begin = self.local2utc(dt=begin)
            end = self.local2utc(dt=end)

            logging.info("Assuming the invoice from period in UTC (%s) instead of local time (%s)" % (begin, local_begin))
            logging.info("Assuming the invoice TO period in UTC (%s) instead of local time (%s)" % (end, local_end))

            # call the function for creation of invoice
            self.calc_and_create(tenant_id, begin, end, local_begin, local_end, date)

    # convert the local time to UTC
    def local2utc(self, dt):

        """local time to utc time."""
        from_zone = tz.gettz(datetime.datetime.now(tz.tzlocal()).tzname())
        to_zone = tz.gettz('UTC')
        local = dt.replace(tzinfo=from_zone)
        return local.astimezone(to_zone).replace(tzinfo = None)

    # date check and decision
    # Invoke invoice creation process if Creation date is today
    # and Invoice is not generated for the period.
    def date_check(self, creation_date, tenant_id, date):

        # If today is creation day of tenant
        if date.day == creation_date.day:

            self.date_process(tenant_id, creation_date, date)

        # today is not tenant creation date
        # no need to attempt for invoice creation
        # But will check for if invoice is missed for the month
        else:

            logging.info("Tenant %s's creation date (%s) is not matching today's date %s, Not creating the invoice but will check for missed invoices" % (tenant_id, creation_date.day, date))        
            
            # Get the invoice using Cloudkitty client
            invoice = ck.reports.get_invoice(tenant_id=tenant_id)

            # dict for storing dates
            invoice_date_list = defaultdict(list)

            # if invoice exists
            # that is not first run
            if invoice:

                    # for storing items in dict
                    for items in invoice:

                        # take date from invoice dict
                        invoice_date = items.invoice_date

                        # append invoice dates
                        invoice_date_list[tenant_id].append(invoice_date)
                        invoice_date_for_tenant = invoice_date_list.get(tenant_id, None)

                    # to find latest invoice date
                    invoice_date_latest = max(invoice_date_for_tenant)
                    invoice_date_latest = datetime.datetime.strptime(invoice_date_latest, '%Y-%m-%dT%H:%M:%SZ')
                    invoice_month_latest = invoice_date_latest.month
                    invoice_day_latest = invoice_date_latest.day
                    today = date.day

                    if today > invoice_day_latest:
                        
                            # list for date range
                            tmpDate = []
                            for d in self.spanning_months(invoice_date_latest, date):
                                tmpDate.append({"month":d.month, "year":d.year})
                                
                                # for the dates
                                for x in tmpDate:
                                        date = date.replace(month=x['month'], day=invoice_day_latest, year=x['year'])
                                        logging.info("Creating the missed invoice for tenant %s and for date %s" % (tenant_id, date))
                                        self.date_process(tenant_id, creation_date, date)

            # first invoice
            else:
                    
                    creation_date = creation_date.replace(tzinfo=None)

                    creation_day = creation_date.day

                    creation_month = creation_date.month

                    today = date.day

                    current_month = date.month

                    # for checking the missed invoices
                    if today > creation_day:
                        
                        # list for date range
                        tmpDate = []
                        for d in self.spanning_months(creation_date, date):
                                tmpDate.append({"month":d.month, "year":d.year})
                                
                                # for the dates
                                for x in tmpDate:
                                         date = date.replace(month=x['month'], day=creation_day, year=x['year'])
                                         logging.info("Creating the missed first invoice for tenant %s and for date %s" % (tenant_id, date))
                                         self.date_process(tenant_id, creation_date, date)

    def spanning_months(self, start, end):
   
        # If the end date is not greater than
        # raise assertion exception
        assert start <= end
        current = start.year * 12 + start.month
        end = end.year * 12 + end.month - 1
        while current <= end:
            yield datetime.date(current // 12, current % 12 + 1, 1)
            current += 1

    # Process and insert Dict to Table
    def dict_create_insert(self, big_dict, tenant_id, begin, end, local_begin, local_end, date):

        # total amount for adding in tables 
        total_amount = big_dict['dict_all_cost_total']

        # dict json dumped for inserting to DB
        final_dict = json.dumps(big_dict)

        # Fetch tenant details
        tenant_details = keystone.tenants.get(tenant_id)

        # get tenant_name
        tenant_name = tenant_details.name

        # begin month and year calculation
        begin_month = begin.month
        begin_year = begin.year
        begin_month = str(begin_month)
        begin_year = str(begin_year)

        # invoice id set
        invoice_id = tenant_name + '-' + begin_month + '-' + begin_year

        paid_cost = '0.0'
        balance_cost = total_amount
        payment_status = '0'

        # for invoice insert
        kwargs = {
            "invoice_id":invoice_id,
            "invoice_date":date,
            "invoice_period_from":local_begin,
            "invoice_period_to":local_end,
            "tenant_id":tenant_id,
            "invoice_data":final_dict,
            "tenant_name":tenant_name,
            "total_cost":total_amount,
            "paid_cost":paid_cost,
            "balance_cost":balance_cost,
            "payment_status":payment_status
        }

        print kwargs

        # final_dict exists
        if final_dict:

            # add the invoice using cloudkitty CLI
            ck.reports.add_invoice(**kwargs)

    # Calculataion of Cost for tenant for the particular period
    # Create necessary dict
    # process and fetch necessary values
    # adding the entries to Dict
    def calc_and_create(self, tenant_id, begin, end, local_begin, local_end, date):

        # Mega Dict which holds all necessary cost details
        big_dict = {
                'dict_compute': {},
                'dict_inbound': {},
                'dict_outbound': {},
                'dict_volume': {},
                'dict_floating': {},
                'dict_cloud_storage': {},
                'dict_instance_addon': {},
                'dict_tenant_addon': {},
                'dict_image_snapshot': {},
                'dict_total_all': {},
                'dict_all_cost_total': {}
        }

        # instance dict
        instance_id_dict = {}
        instance_size_list = {}

        # Instance list fetch
        instances = nt.servers.list(search_opts={'all_tenants':1, 'tenant_id':tenant_id})

        # Instance Flavor list fetch
        instance_flavor_types = nt.flavors.list()

        # Create a Dict of flavor with ID and Name
        # We can use ot for comparison to find flavor of instance
        for flavors in instance_flavor_types:

            instance_size_list[flavors.id] = flavors.name

        # Instance details as needed
        for instance in instances:

            instance_id = instance.id
            instance_name = instance.name

            # Getting instance details
            instance_size = nt.servers.get(instance_id)
            instance_size = instance_size.flavor['id']

            # Compating the values with list to get flavor
            instance_size_name = instance_size_list[instance_size]

            logging.info("Getting the necessary instance details for tenant %s" % (tenant_id))
            # Dict with necessary details on instance
            instance_id_dict[instance_id] = instance_name, instance_size_name


        # compute charges based on instances
        for a, b in instance_id_dict.iteritems():

            compute_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='compute', instance_id=a)
            logging.info("Calculating compute charges for the tenant %s" % (tenant_id))
            big_dict['dict_compute'][a] = b[0], b[1], compute_value_for_instance

        # inbound charges based on instances
        for a, b in instance_id_dict.iteritems():

            inbound_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.bw.in', instance_id=a)
            logging.info("Calculating Inbound charges for the tenant %s" % (tenant_id))
            big_dict['dict_inbound'][a] = b[0], b[1], inbound_value_for_instance

        # outbound charges based on instances
        for a, b in instance_id_dict.iteritems():

            outbound_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.bw.out', instance_id=a)
            logging.info("Calculating outbound charges for the tenant %s" % (tenant_id))
            big_dict['dict_outbound'][a] = b[0], b[1], outbound_value_for_instance

        # instance add-on charges based on instances
        for a, b in instance_id_dict.iteritems():

            instance_addon_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='instance.addon', instance_id=a)
            logging.info("Calculating instance addon charges for the tenant %s" % (tenant_id))
            big_dict['dict_instance_addon'][a] = b[0], b[1], instance_addon_value_for_instance

        # Volume calculation
        volume = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='volume')
        logging.info("Calculating volume charges for the tenant %s" % (tenant_id))
        big_dict['dict_volume'] = volume

        # floating calculations
        floating = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.floating')
        logging.info("Calculating floating IP charges for the tenant %s" % (tenant_id))
        big_dict['dict_floating'] = floating

        # image/snapshot calculations
        image_snapshot = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='image')
        logging.info("Calculating image/snapshot charges for the tenant %s" % (tenant_id))
        big_dict['dict_image_snapshot'] = image_snapshot

        # tenant.addon calculations
        tenant_addon = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='tenant.addon')
        logging.info("Calculating Tenant addon charges for the tenant %s" % (tenant_id))
        big_dict['dict_tenant_addon'] = tenant_addon

        # Total Charge based on instance
        for a, b in instance_id_dict.iteritems():

            total_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, instance_id=a)
            logging.info("Calculating Overall charges(based on instances) for the tenant %s" % (tenant_id))
            big_dict['dict_total_all'][a] = b[0], b[1], total_value_for_instance

        # Cloud storage calculation
        cloud_storage = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='cloudstorage')
        logging.info("Calculating cloud storages charges for the tenant %s" % (tenant_id))
        big_dict['dict_cloud_storage'] = cloud_storage

        # Total Charge calculations (Overall including all costs all instances)
        total_all_cost = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end)
        logging.info("Calculating Total charges(Overall including all costs all instances) for the tenant %s" % (tenant_id))
        big_dict['dict_all_cost_total'] = total_all_cost

        # Process the Dict and insert to Table
        self.dict_create_insert(big_dict, tenant_id, begin, end, local_begin, local_end, date)

    def tenant_addon_rate(self):
   

        logging.info("Inside the tenant add-on rating section")

 
        # get todays date
        ta_today_date = datetime.datetime.today()
        
        # can edit date for debugging and verification
        # ta_today_date = ta_today_date.replace(day=01, month=06, year=2016, hour=00, minute=00, second=00, microsecond=0)
        
        # Take current month and year
        ta_month = ta_today_date.month
        ta_year = ta_today_date.year
        
        # set the begin period
        ta_begin_period = ta_today_date.replace(day=1, 
                                          hour=0, 
                                          minute=0,
                                          second=0, 
                                          microsecond=0)
        
        # set the end period
        ta_end_date_period = calendar.monthrange(ta_year, ta_month)[1]
        ta_end_period = ta_today_date.replace(day=ta_end_date_period, 
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
            ta_tenant_id = mapping_details.value
        
            # get the available rated dataframes for tenant.addon
            list_rated_frames = ck.storage.dataframes.list(resource_type='tenant.addon', 
                                                           begin=ta_begin_period, 
                                                           end=ta_end_period, 
                                                           tenant_id=ta_tenant_id)
        
            # frame count to decide the course of action
            frames_count = len(list_rated_frames)
        
            # for adding necessary details
            rate = mapping_details.cost
        
            # get the tenant details
            try:
        
                ta_tenant =  keystone.tenants.get(ta_tenant_id)
                dicts = {'name': ta_tenant.name, 'description': ta_tenant.description, 
                         'tenant_id': ta_tenant_id, 'creation_time': ta_tenant.creation_date, 
                         'timezone': ta_tenant.timezone}
        
            except:
        
                dicts = {'tenant_id': ta_tenant_id}
        
            # if tenant addon is not rated for this month
            if frames_count == 0:
       
                logging.info("Adding the tenant addon data to rated_data_frames for tenant %s" % (ta_tenant_id))
                # add dataframes
                add_rated_frames = ck.storage.dataframes.create(res_type='tenant.addon',
                                                                begin=ck_utils.dt2iso(ta_begin_period),
                                                                end=ck_utils.dt2iso(ta_begin_period),
                                                                tenant_id=ta_tenant_id,
                                                                unit='tenant', 
                                                                qty='1', 
                                                                rate=rate, 
                                                                desc=dicts)

# Execute billing engine
if __name__ == "__main__":
        BillingEngine().tenant_addon_rate()
        BillingEngine().run()
