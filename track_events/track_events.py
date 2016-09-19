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

# Parsing input files
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--event_conf", default=None,
                    help="Specify local track_event.conf file", metavar="FILE")
parser.add_argument("-o", "--openstack_conf", default=None,
                    help="Specify openstack conf file location(nova/neutron)", metavar="FILE")
args, remaining_argv = parser.parse_known_args()

# Processing Local conf file
if args.event_conf:
    config = ConfigParser.RawConfigParser()
    config.read([args.event_conf])
    configdetails_section1 = dict(config.items("configdetails_section1"))

# Processing openstack Conf file
if args.openstack_conf:
    config = ConfigParser.RawConfigParser()
    config.read([args.openstack_conf])
    openstackpath = config.read([args.openstack_conf])
    oslo_messaging_rabbit = dict(config.items("oslo_messaging_rabbit"))

# Necessary details which is needed to establish 
# connection in common despite of arguments
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

# calculating total number of arguments 
# to decide config details fetching
total_args = len(sys.argv)

# If there are only two arguments 
# (Only local configuration file is supplied)
if total_args == 2:
    parser.set_defaults(**configdetails_section1)
    args = parser.parse_args(remaining_argv)
    BROKER_URI = args.broker_uri

# if there is three arguments were supplied 
# (Local configuration file and neutron/nova conf supplied)
elif total_args == 3:
    parser.set_defaults(**oslo_messaging_rabbit)
    args = parser.parse_args(remaining_argv)
    
    # Fetch rabbitmq uesrname and password
    # from Nova/neutron file
    username = args.rabbit_userid
    password = args.rabbit_password
    
    # assign rabitmq username and passoword 
    # to BROKER_URI
    BROKER_URI = "amqp://" + username + ":" + password + "@localhost:5672/%2F"

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
        try:
            self.event_process(event_type)
        except Exception, e:
            logging.info(repr(e))
            
    # Various event processes and actions
    def event_process(self, event_type):
        if event_type == "compute.instance.create.start":
            self.instance_created_start_action()
            
        if event_type == "compute.instance.create.error":
            self.instance_created_error_action()
            
        if event_type == "compute.instance.create.end":
            self.instance_created_end_action()
           
        if event_type == "compute.instance.delete.start":  
            self.instance_deleted_start_action()
   
        if event_type == "compute.instance.delete.end":  
            self.instance_deleted_end_action()
   
        if event_type == "compute.instance.resize.confirm.start":  
            self.instance_resize_start_action()
            
        if event_type == "compute.instance.resize.confirm.end":  
            self.instance_resize_end_action()
            
        if event_type == "volume.create.start":  
            self.volume_create_start_action()            

        if event_type == "volume.create.end":  
            self.volume_create_end_action() 
            
        if event_type == "volume.delete.start":  
            self.volume_delete_start_action()            

        if event_type == "volume.delete.end":  
            self.volume_delete_end_action()
    
        if event_type == "volume.usage":  
            self.volume_usage()            
                   
    # actions to be performed on instance creation start
    def instance_created_start_action(self):
        logging.info("There is a new instance creation process started in devstack")
        
    # actions to be performed on instance creation error
    def instance_created_error_action(self):
        logging.info("There was a attempt to create new instance, But there was a error")
        
    # actions to be performed on instance creation completion
    def instance_created_end_action(self):
        logging.info("New instance created succesfully in devstack")

    # actions to be performed on instance deletion start
    def instance_deleted_start_action(self):
        logging.info("Instance deletion action started in devstack")
    
    # actions to be performed on instance deletion
    def instance_deleted_end_action(self):
        logging.info("Instance deletion ends in devstack")
        
    # actions to be performed on instance resize start
    def instance_resize_start_action(self):
        logging.info("Instance resize action started in devstack")
        
    # actions to be performed on instance resize end
    def instance_resize_end_action(self):
        logging.info("Instance resize action completed in devstack")
       
    # actions to be performed on volume create start
    def volume_create_start_action(self):
        logging.info("Volume creation started in devstack")
        
    # actions to be performed on volume create end
    def volume_create_end_action(self):
        logging.info("Volume creation ends in devstack")
    
    # actions to be performed on volume deletion start
    def volume_delete_start_action(self):
        logging.info("Volume deletion started in devstack")
        
    # actions to be performed on volume deletion end
    def volume_delete_end_action(self):
        logging.info("Volume deletion ends in devstack")

    # actions to be performed on volume usage details event
    def volume_usage(self):
        logging.info("Volume usage details")    
  

if __name__ == "__main__":
    logging.info("Connecting to broker {}".format(BROKER_URI))
    with BrokerConnection(BROKER_URI) as connection:
        TrackEvents(connection).run()
