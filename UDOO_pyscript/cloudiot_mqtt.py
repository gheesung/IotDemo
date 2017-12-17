#!/usr/bin/env python

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Adapted from Google example for connnecting to CLoud IoT Core via MQTT, using JWT.
This example is modified for UDOO Quad read the temperature/humidity (DHT11) from 
Arduino to Linux via serial port interface. 
"""

import argparse
import datetime
import os
import time

import jwt
import paho.mqtt.client as mqtt

import serial
import time
import re
import json

# [START iot_mqtt_jwt]
def create_jwt(project_id, private_key_file, algorithm):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
        Args:
         project_id: The cloud project ID this device belongs to
         private_key_file: A path to a file containing either an RSA256 or
                 ES256 private key.
         algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
        Returns:
            An MQTT generated from the given project_id and private key, which
            expires in 20 minutes. After 20 minutes, your client will be
            disconnected, and a new JWT will have to be generated.
        Raises:
            ValueError: If the private_key_file does not contain a known key.
        """

    token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    print('Creating JWT using {} from private key file {}'.format(
            algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm)
# [END iot_mqtt_jwt]


# [START iot_mqtt_config]
def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return '{}: {}'.format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print('on_connect', mqtt.connack_string(rc))


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print('on_disconnect', error_str(rc))


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    print('on_publish')

def on_subscribe(unused_client, unused_userdata, unused_mid, unused_qos):
    """Paho callback when subscribe to broker."""
    print('on_subscribe')

def on_message(client, userdata, msg):
    print('on_message: '+ str(msg.payload))

def get_client(
        project_id, cloud_region, registry_id, device_id, private_key_file,
        algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client = mqtt.Client(
            client_id=('projects/{}/locations/{}/registries/{}/devices/{}'
                       .format(
                               project_id,
                               cloud_region,
                               registry_id,
                               device_id)))

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(
            username='unused',
            password=create_jwt(
                    project_id, private_key_file, algorithm))

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_publish = on_publish
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    # Start the network loop.
    client.loop_start()

    return client
# [END iot_mqtt_config]

# Serial Port Handler
class SerialPortManager:
    
    def __init__(self):
        self.port = serial.Serial('/dev/ttymxc3',9600,timeout=1)

    def write(self, message):
        print("Writing data to serial port: " + message)
        self.port.write(message)
        self.port.flushOutput()

    def readx(self):
        return self.port.readline()

    def close(self):
        return self.port.close()

# [END Serial Port Handler]

def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=(
            'Example Google Cloud IoT Core MQTT device connection code.'))
    parser.add_argument(
            '--project_id',
            default=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            help='GCP cloud project name')
    parser.add_argument(
            '--registry_id', required=True, help='Cloud IoT Core registry id')
    parser.add_argument(
            '--device_id', required=True, help='Cloud IoT Core device id')
    parser.add_argument(
            '--private_key_file',
            required=True, help='Path to private key file.')
    parser.add_argument(
            '--algorithm',
            choices=('RS256', 'ES256'),
            required=True,
            help='Which encryption algorithm to use to generate the JWT.')
    parser.add_argument(
            '--cloud_region', default='us-central1', help='GCP cloud region')
    parser.add_argument(
            '--ca_certs',
            default='roots.pem',
            help=('CA root from https://pki.google.com/roots.pem'))
    parser.add_argument(
            '--num_messages',
            type=int,
            default=100,
            help='Number of messages to publish.')
    parser.add_argument(
            '--message_type',
            choices=('event', 'state'),
            default='event',
            help=('Indicates whether the message to be published is a '
                  'telemetry event or a device state message.'))
    parser.add_argument(
            '--mqtt_bridge_hostname',
            default='mqtt.googleapis.com',
            help='MQTT bridge hostname.')
    parser.add_argument(
            '--mqtt_bridge_port',
            choices=(8883, 443),
            default=8883,
            type=int,
            help='MQTT bridge port.')
    parser.add_argument(
            '--jwt_expires_minutes',
            default=20,
            type=int,
            help=('Expiration time, in minutes, for JWT tokens.'))

    return parser.parse_args()




# [START iot_mqtt_run]
def main():
    args = parse_command_line_args()

    # Publish to the events or state topic based on the flag.
    sub_topic = 'events' if args.message_type == 'event' else 'state'

    mqtt_topic = '/devices/{}/{}'.format(args.device_id, sub_topic)
    mqtt_config_topic = '/devices/{}/config'.format(args.device_id)

    jwt_iat = datetime.datetime.utcnow()
    jwt_exp_mins = args.jwt_expires_minutes
    client = get_client(
        args.project_id, args.cloud_region, args.registry_id, args.device_id,
        args.private_key_file, args.algorithm, args.ca_certs,
        args.mqtt_bridge_hostname, args.mqtt_bridge_port)

    # subscribe to config topic 
    client.subscribe(mqtt_config_topic)

    #set up the serial port runner
    serialMgr = SerialPortManager()

    # Publish num_messages mesages to the MQTT bridge when there is message at 
    # serial port. Currently, the arduino side is reading the temperature 
    # every 5 minutes
    i = 0
    while True:

        #line = serialMgr.readx()
        line = serialMgr.readx()
        if len(line) > 0:
            i = i + 1
            print("Read from serial port: " + line.decode('ascii'))
            sensordata = json.loads(line.decode('ascii')    )
            sensordata['registryID'] = args.registry_id
            sensordata['deviceID'] = args.device_id
            currentDT = datetime.datetime.now()
            sensordata['datetime'] = currentDT.strftime("%Y-%m-%d %H:%M:%S")
            
            line = json.dumps(sensordata)

            payload = '{}/{}-payload-{}'.format(
                    args.registry_id, args.device_id, line)
            print('Publishing message {}: \'{}\''.format(
                    i, payload))
            
            seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
            if seconds_since_issue > 60 * jwt_exp_mins:
                #print('Refreshing token after {}s').format(seconds_since_issue)
                client.loop_stop()
                jwt_iat = datetime.datetime.utcnow()
                client = get_client(
                    args.project_id, args.cloud_region,
                    args.registry_id, args.device_id, args.private_key_file,
                    args.algorithm, args.ca_certs, args.mqtt_bridge_hostname,
                    args.mqtt_bridge_port)
                # subscribe to config topic 
                client.subscribe(mqtt_config_topic)

            # Publish "payload" to the MQTT topic. qos=1 means at least once
            # delivery. Cloud IoT Core also supports qos=0 for at most once
            # delivery.
            client.publish(mqtt_topic, line, qos=1)

        # Send events every second. State should not be updated as often
        time.sleep(1 if args.message_type == 'event' else 5)

    # End the network loop and finish.
    client.loop_stop()
    serialMgr.close()

    print('Finished.')
# [END iot_mqtt_run]


if __name__ == '__main__':
    main()
