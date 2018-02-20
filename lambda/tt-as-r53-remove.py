import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def handler(event, context):
    if event == "cli":
        logger.info("Command Line Invoked")
    else:
        logger.info(json.dumps(event))
        asg = boto3.client('autoscaling')
        r53 = boto3.client('route53')
        ec2 = boto3.resource('ec2')

        # Get the SNS message data into a dict
        message = json.loads(event["Records"][0]["Sns"]["Message"])
        logger.info(message)

        # Get the custom notification data into a dict and assign to vars
        notification_meta = json.loads(message["NotificationMetadata"])
        r53_zone = notification_meta["r53_zone"]
        hc_id = notification_meta["hc_id"]

    try:
        instance = ec2.Instance(message["EC2InstanceId"])
        logger.info(instance.public_ip_address)

        # Create a new Route53 record
        r53.change_resource_record_sets(
            HostedZoneId=r53_zone,
            ChangeBatch={
            'Changes': [
                {
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                    'Name': "web.tt.internal.",
                    'Type': 'A',
                    'Weight': 10,
                    'SetIdentifier': 'web-tt ' + message["EC2InstanceId"],
                    'ResourceRecords': [
                    {
                        'Value': instance.public_ip_address
                    }
                    ],
                    'HealthCheckId': hc_id,
                    'TTL': 60
                }
                }
            ]
            }
        )


        response = asg.complete_lifecycle_action(
            LifecycleHookName=message["LifecycleHookName"],
            LifecycleActionToken=message["LifecycleActionToken"],
            AutoScalingGroupName="tt-as-group-instance",
            LifecycleActionResult="CONTINUE",
            InstanceId=message["EC2InstanceId"]
            )
        logger.info(response)
    except Exception as e:
        logger.error("Error: %s", str(e))

if __name__ == '__main__':
    print(handler("cli", ""))
