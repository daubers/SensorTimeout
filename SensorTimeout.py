import paho.mqtt.client as mqtt
from threading import Lock
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.utils import format_datetime
import argparse


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj

class SenseFail:

    @staticmethod
    def sendmail(topic, timestamp, from_address, to_address, mail_user, mail_password, mail_server, mail_port):
        msg = MIMEText("Topic {0} was last seen at {1}".format(topic, timestamp.isoformat()))

        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = 'Sensor node missed check in'
        msg['From'] = from_address
        msg['To'] = to_address
        msg['Date'] = format_datetime(datetime.now())

        mail_user = mail_user
        mail_pwd = mail_password
        smtpserver = smtplib.SMTP(mail_server, mail_port)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo()
        smtpserver.login(mail_user, mail_pwd)
        smtpserver.sendmail(msg['from'], msg['To'], msg.as_string())
        smtpserver.close()

    def topic_seen(self, topic):
        if topic == "/SenseFail/Report":
            self.client.publish("/SenseFail/Report/Data", json.dumps(self.topic_last_seen, default=date_handler))
        elif "error" in topic.lower():
            pass
        elif topic == "/SenseFail/Report/Data":
            pass
        else:
            self.topic_last_seen[topic] = datetime.now()

    def check_topics(self):
        deleted_topics = []
        for topic, timestamp in self.topic_last_seen.items():
            if timestamp < datetime.now() - timedelta(minutes=10):
                SenseFail.sendmail(topic, timestamp, self.from_address, self.to_address, self.mail_user,
                                   self.mail_password, self.mail_server, self.mail_port)
                deleted_topics.append(topic)
        for topic in deleted_topics:
            del self.topic_last_seen[topic]

    def __on_message(self, client, userdata, message):
        self.topic_seen(message.topic)

    def __init__(self, server, to_address, from_address,
                 mail_server, mail_port, mail_user, mail_password, username=None, password=None, ):
        self.server = server
        self.username = username
        self.password = password
        self.to_address = to_address
        self.from_address = from_address
        self.mail_server = mail_server
        self.mail_port = mail_port
        self.mail_user = mail_user
        self.mail_password = mail_password
        self.client = mqtt.Client()
        self.topic_last_seen = {}
        self.topic_last_seen_lock = Lock()
        self.client.on_message = self.__on_message

    def run(self):

        if self.username is not None:
            self.client.username_pw_set(self.username, self.password)
        self.client.connect(self.server)
        self.client.subscribe("#")
        rc = 0
        last_check = datetime.now() - timedelta(hours=1)
        while rc == 0:
            rc = self.client.loop()
            if last_check < datetime.now() - timedelta(minutes=5):
                self.check_topics()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for MQTT topics and notify after a 10 minute interval")
    parser.add_argument("--mail-to", help="E-Mail To Address")
    parser.add_argument("--mail-from", help="E-Mail from address")
    parser.add_argument("--smtp-server", help="SMTP server address")
    parser.add_argument("--smtp-port", help="SMTP Port", type=int)
    parser.add_argument("--smtp-username", help="SMTP Username")
    parser.add_argument("--smtp-password", help="SMTP Password")
    parser.add_argument("--mqtt-server", help="MQTT Server Address")
    parser.add_argument("--mqtt-username", help="MQTT Username", default=None)
    parser.add_argument("--mqtt-password", help="MQTT Password", default=None)
    args = parser.parse_args()
    test = SenseFail(args.mqtt_server, args.mail_to, args.mail_from, args.smtp_server,
                     args.smtp_port, args.smtp_username, args.smtp_password, args.mqtt_username, args.mqtt_password)
    test.run()
