import argparse
import sys
import ConfigParser
import json, ast
import pprint
import logging
from subprocess import Popen, PIPE
from kombu import BrokerConnection
from kombu import Exchange
from kombu import Queue
from kombu.mixins import ConsumerMixin
from twilio.rest import TwilioRestClient
from keystoneclient.v2_0 import client as kclient
from keystoneclient.auth.identity import v3
from keystoneclient import session

# Parsing input files
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--event_conf", default=None,
                    help="Specify local track_event.conf file", metavar="FILE")
args, remaining_argv = parser.parse_known_args()

# Processing Local conf file
if args.event_conf:
    config = ConfigParser.RawConfigParser()
    config.read([args.event_conf])
    configdetails_section1 = dict(config.items("configdetails_section1"))

# Necessary details which is needed to establish 
parser.set_defaults(**configdetails_section1)
args = parser.parse_args(remaining_argv)
LOG_FILE = args.log_file 
EXCHANGE_NAME1 = args.exchange_name1
EXCHANGE_NAME2 = args.exchange_name2
ROUTING_KEY = args.routing_key
QUEUE_NAME = args.queue_name
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

# Openstack Credentials for establishing Keystone connection
tenant_name = args.tenant_name
auth_url = args.auth_url
username = args.username
password = args.password
region_name = args.region_name

# Twilio Credentials
account_sid = args.account_sid
auth_token = args.auth_token
from_mob_no = args.from_mob_no

# Credentials for establishing Keystone Connection.
kwargs_conn = {
    "tenant_name":tenant_name,
    "auth_url":auth_url,
    "username":username,
    "password":password,
    "region_name": region_name
}

# Establish Connection With Keystone
keystone = kclient.Client(**kwargs_conn)

# Establish Twilio Connection
tclient = TwilioRestClient(account_sid, auth_token)

# calculating total number of arguments 
# to decide config details fetching
total_args = len(sys.argv)

# If there are only two arguments 
# (Only local configuration file is supplied)
if total_args == 2:
    parser.set_defaults(**configdetails_section1)
    args = parser.parse_args(remaining_argv)
    BROKER_URI = args.broker_uri

# class for tracking Events
class TrackEvents(ConsumerMixin):

    # initializing the connections
    def __init__(self, connection):
        self.connection = connection
        return
    
    # Getting the connection established with 
    # consumer on exchanges nova and openstack
    def get_consumers(self, consumer, channel):
        exchange1 = Exchange(EXCHANGE_NAME1, type="topic", durable=False)
        queue1 = Queue(QUEUE_NAME, exchange1, routing_key=ROUTING_KEY,
            durable=False, auto_delete=True, no_ack=True)
        exchange2 = Exchange(EXCHANGE_NAME2, type="topic", durable=False)
        queue2 = Queue(QUEUE_NAME, exchange2, routing_key=ROUTING_KEY,
            durable=False, auto_delete=True, no_ack=True)
        queues = [queue1, queue2]
        return [ consumer(queues, callbacks=[ self.on_message ]) ]

    # actions to be performed on message 
    # receive on fanout nova
    def on_message(self, body, message):
        try:
            self._handle_message(body)
        except Exception, e:
            logging.info(repr(e))

    # Handling the received messages
    def _handle_message(self, body):

        # eval and do json.dumps
        body = ast.literal_eval(json.dumps(body))

        # Fetching the oslo.message
        oslo_message = body['oslo.message']

        # creating oslo_message_dict 
        oslo_message_dict = json.loads(oslo_message)
 
        # fetching event type
        event_type = oslo_message_dict['event_type']
        payload = oslo_message_dict['payload']
        tenant_id = payload['tenant_id']
        dicts = {'event_type': event_type, 'tenant_id':tenant_id}
        try:
            self.event_process(dicts)
        except Exception, e:
            logging.info(repr(e))
            
    # Various event processes and actions
    def event_process(self, dicts):

        tenant_id = dicts['tenant_id']
        tenant_details = keystone.tenants.get(tenant_id)
        mobile_number = tenant_details.mobile_number

        if dicts['event_type'] == "compute.instance.create.start":
            self.instance_created_start_action(mobile_number)

        if dicts['event_type'] == "compute.instance.create.error":
            self.instance_created_error_action(mobile_number)
            
        if dicts['event_type'] == "compute.instance.create.end":
            self.instance_created_end_action(mobile_number)
           
        if dicts['event_type'] == "compute.instance.delete.start":  
            self.instance_deleted_start_action(mobile_number)
   
        if dicts['event_type'] == "compute.instance.delete.end":  
            self.instance_deleted_end_action(mobile_number)
   
        if dicts['event_type'] == "volume.create.start":  
            self.volume_create_start_action(mobile_number)            

        if dicts['event_type'] == "volume.create.end":  
            self.volume_create_end_action(mobile_number) 
            
        if dicts['event_type'] == "volume.delete.start":  
            self.volume_delete_start_action(mobile_number)            

        if dicts['event_type'] == "volume.delete.end":  
            self.volume_delete_end_action(mobile_number)
    
    # actions to be performed on instance creation start
    def instance_created_start_action(self, mobile_number):
        message = tclient.messages.create(body="Instance Creation Process initiated Succesfully",
                to=mobile_number,   
                from_=from_mob_no)
        logging.info("From number %s" % (from_mob_no)) 
        logging.info("There is a new instance creation process initiated - Message SID: %s" % (message.sid))
        
    # actions to be performed on instance creation completion
    def instance_created_end_action(self, mobile_number):
        message = tclient.messages.create(body="Instance Creation Process Completed Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a new instance creation process Completed Succesfully - Message SID: %s" % (message.sid))

    # actions to be performed on instance deletion start
    def instance_deleted_start_action(self, mobile_number):
        message = tclient.messages.create(body="Instance Deletion Process initiated Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a instance deletion process initiated - Message SID: %s" % (message.sid))

    # actions to be performed on instance deletion
    def instance_deleted_end_action(self, mobile_number):
        message = tclient.messages.create(body="Instance Deletion Process completed Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a instance deletion process initiated - Message SID: %s" % (message.sid))

    # actions to be performed on volume create start
    def volume_create_start_action(self, mobile_number):
        message = tclient.messages.create(body="Volume Creation Process initiated Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a new Volume creation process initiated - Message SID: %s" % (message.sid))

    # actions to be performed on volume create end
    def volume_create_end_action(self, mobile_number):
        message = tclient.messages.create(body="Volume Creation Process completed Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a new Volume Creation process Completed - Message SID: %s" % (message.sid))

    # actions to be performed on volume deletion start
    def volume_delete_start_action(self, mobile_number):
        message = tclient.messages.create(body="Volume Deletion Process initiated Succesfully",
                to=mobile_number,    
                from_=from_mob_no)
        logging.info("There is a Volume deletion process initiated - Message SID: %s" % (message.sid))

    # actions to be performed on volume deletion end
    def volume_delete_end_action(self, mobile_number):
        message = tclient.messages.create(body="Volume deletion Process Completed Succesfully",
                to=mobile_number,
                from_=from_mob_no)
        logging.info("There is a Volume Deletion process Completed - Message SID: %s" % (message.sid))

if __name__ == "__main__":
    logging.info("Connecting to broker {}".format(BROKER_URI))
    with BrokerConnection(BROKER_URI) as connection:
        TrackEvents(connection).run()
