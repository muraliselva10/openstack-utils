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
from collections import defaultdict
import ConfigParser
import datetime
import logging
import json
import datetime
import dateutil.relativedelta
import MySQLdb 
from MySQLdb import OperationalError


# For importing details from config file
config = ConfigParser.RawConfigParser()
config.read('/etc/cloudkitty/cloudkitty.conf')

# Fetch details from config file
# For connection part
connection = dict(config.items("keystone_authtoken"))

# kwargs for connection
kwargs = {
    "tenant_name":"admin",
    "auth_url":'http://127.0.0.1:5000/v2.0',
    "username":"admin",
    "password":connection['password'],
}

# DB connection
db = MySQLdb.connect("localhost","root",kwargs.get('password'),"cloudkitty" )
db1 = MySQLdb.connect("localhost","root",kwargs.get('password'),"keystone" )

# prepare a cursor object using cursor() method
cursor = db.cursor()
cursor1 = db1.cursor()

# Establish the connection Keystone
keystone = kclient.Client(**kwargs)

# Establish the connection Cloudkitty
ck = client.get_client("1", **kwargs)

# Establish the connection NOVA
nt = nova_client.Client("2", kwargs.get('username'), kwargs.get('password'), kwargs.get('tenant_name'), kwargs.get('auth_url'))

# Logging the items
# Log Definition
logging.basicConfig(filename='/var/log/cloudkitty/automated_billing.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

# current date operations
mylist = []
today = datetime.datetime.today()
mylist.append(today)
date = mylist[0]

class BillingEngine():
    
    # Getting the tenant list 
    # Fetch the creation_date of tenant if exists
    def get_tenants(self):
    
        # Fetch tenant list
        tenants_list = keystone.tenants.list()
    
        # Fetch tenant ID
        for tenant in tenants_list:
            tenant_id = tenant.id
    
            # Fetch the extra details from project table
            # Creation date fetch
            sql1 = "SELECT extra FROM project where id='%s'" % (tenant_id)
            cursor1.execute(sql1)
            rows = cursor1.fetchall()
    
            # for each extra info
            for row in rows:
                    # parsing inside extra field
                    for value in row:
                            # Decode json 
                            if 'creation_date' in json.loads(value):
                                    logging.info("Fetching only the tenants which have creation date and elligible for billing")
                                    # fetch the creation_date
                                    ivalue = [json.loads(value)['creation_date'] for value in row ]
                                    creation_date = ivalue[0]
                                    self.date_check(creation_date, tenant_id)
    
    # date check and decision
    # Assume creation_date for unclear end date(29,30,31)
    # Invoke invoice creation process if Creation date is today
    # and Invoice is not generated for the period.
    def date_check(self, creation_date, tenant_id):
    
            # Format creation date
            creation_date = datetime.datetime.strptime(creation_date, '%Y-%m-%d')
    
            # Creation date of tenant is unclear
            # creation date is  29,30,31
            if creation_date.day in (29, 30, 31):
                    logging.info("Assuming the creation date for tenant %s as it have no clear creation date" % (tenant_id))
                    # replace and assume end date
                    creation_date = creation_date.replace(day=28)
    
            # If today is creation day of tenant
            if date.day == creation_date.day:
    
                    logging.info("Creation date of tenant %s is today %s, Gonna check invoice_details table for next step" % (tenant_id, date))
                    # select last invoice_date for tenant
                    sql2 = "SELECT invoice_date FROM invoice_details where tenant_id='%s' order by id desc limit 1" % (tenant_id)
                    cursor.execute(sql2)
                    rows = cursor.fetchall()
    
                    # Check whether it is first run or subsequent run, 
                    # If it is not first tun
                    if rows:
    
                            logging.info("Checking the last invoice date for report generation for tenant %s" % (tenant_id))
                            for row in rows:
                                    # Invoice date
                                    invoice_date = row[0]
    
                            # invoice date and today date diff
                            diff = date - invoice_date
                            days_diff_from_last_invoice = diff.days
    
                            # If diff is greater than 29 days
                            if days_diff_from_last_invoice > 29:
    
                                    logging.info("Tenant %s is elligible for next invoice creation" % (tenant_id))
                                    # begin date and end date set
                                    begin = date - dateutil.relativedelta.relativedelta(months=1)
                                    end = date - dateutil.relativedelta.relativedelta(days=1)
                                    # call the function for creation of invoice
                                    self.calc_and_create(tenant_id, begin, end)
    
                    # if it is first run
                    else:
                            logging.info("Tenant %s's first invoice creation" % (tenant_id))
                            # begin date and end date set
                            begin = date - dateutil.relativedelta.relativedelta(months=1)
                            end = date - dateutil.relativedelta.relativedelta(days=1)
                            # call the function for creation of invoice
                            self.calc_and_create(tenant_id, begin, end)
    
            # today is not tenant creation date
            # no need to attempt for invoice creation
            else:
                    logging.info("Tenant %s's creation date is not matching today's date %s, Not creating the invoice" % (tenant_id, date))
    
    # Process and insert Dict to Table
    def dict_create_insert(self, big_dict, tenant_id, begin, end):
    
            # dict json dumped for inserting to DB
            final_dict = json.dumps(big_dict)
    
            invoice_id = tenant_id 
    
            # fina_dict exists
            if final_dict:
    
                    logging.info("Inserting the necessary details into invoice_details table for tenant %s invoice period (%s to %s) Invoice date - %s" % (tenant_id, begin, end, date))
                    sql = "INSERT INTO invoice_details(invoice_date, tenant_id, invoice_id, invoice_data, invoice_period_from, invoice_period_to) \
                                   VALUES ( '%s', '%s', '%s', '%s', '%s', '%s' )" % \
                                   (date, tenant_id, invoice_id, final_dict, begin, end)
    
                    try:
    
                            # Execute the SQL command
                            cursor.execute(sql)
    
                            # Commit your changes in the database
                            db.commit()
    
                    except OperationalError as e:
    
                            logging.info("operational error" % (e))
    
                            # Rollback in case there is any error
                            db.rollback()
    
                            # disconnect from server
                            db.close()
    
    
    # Calculataion of Cost for tenant for the particular period
    # Create necessary dict 
    # process and fetch necessary values
    # adding the entries to Dict
    def calc_and_create(self, tenant_id, begin, end):
    
            # Mega Dict which holds all necessary cost details
            big_dict = {
                    'dict_compute': {},
                    'dict_inbound': {},
                    'dict_outbound': {},
                    'dict_volume': {},
                    'dict_floating': {},
                    'dict_total_all': {}
            }
    
            # instance dict
            instance_id_dict = {}
            instance_size_list = {}
    
            # Instance list fetch 
            instances = nt.servers.list(search_opts={'all_tenants':1,'tenant_id':tenant_id})
    
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
            for a,b in instance_id_dict.iteritems():
                    compute_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='compute', instance_id=a)
                    logging.info("Calculating compute charges for the tenant %s" % (tenant_id)) 
                    big_dict['dict_compute'][a] = b[0], b[1], compute_value_for_instance
    
            # inbound charges based on instances
            for a,b in instance_id_dict.iteritems():
                    inbound_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.bw.in', instance_id=a)
                    logging.info("Calculating Inbound charges for the tenant %s" % (tenant_id)) 
                    big_dict['dict_inbound'][a] = b[0], b[1], inbound_value_for_instance
    
            # outbound charges based on instances
            for a,b in instance_id_dict.iteritems():
                    outbound_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.bw.out', instance_id=a)
                    logging.info("Calculating outbound charges for the tenant %s" % (tenant_id)) 
                    big_dict['dict_outbound'][a] = b[0], b[1], outbound_value_for_instance
    
            # Volume calculation
            volume = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='volume')
            logging.info("Calculating volume charges for the tenant %s" % (tenant_id)) 
            big_dict['dict_volume'] = volume
    
            # floating calculations
            floating = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, service='network.floating')
            logging.info("Calculating floating IP charges for the tenant %s" % (tenant_id)) 
            big_dict['dict_floating'] = floating
    
            # Total Charge based on instance
            for a,b in instance_id_dict.iteritems():
                    total_value_for_instance = ck.reports.get_total(tenant_id=tenant_id, begin=begin, end=end, instance_id=a)
                    logging.info("Calculating Overall charges(based on instances) for the tenant %s" % (tenant_id)) 
                    big_dict['dict_total_all'][a] = b[0], b[1], total_value_for_instance
    
            # Process the Dict and insert to Table
            self.dict_create_insert(big_dict, tenant_id, begin, end)

if __name__ == "__main__":
        BillingEngine().get_tenants()
