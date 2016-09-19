# Billing script - Cloudkitty

This is the script for extracting the billing details from Cloudkitty.

Already we have created the script for the Rating or Configuration of pricing in various heads as needed.

So that based on the same every details were captured as needed.

This script will be extracting the details as per the inputs.

It can be able to handle the inputs in following two methods:

- Commandline input.
- Input details using Config file.

As well as the script will be able to produce the results in following ways.

- Tenant_id, begin date, end date available - Will produce the total amount for the tenant in particular date range.

- Tenant_id available - Will produce the total amount for the tenant in whole period despite of dates.

- begin date and end date available - Will produce the total amount between the begin date and date for all the tenants available.

- No values available - Will produce the result despite of dates as well as for all the tenants.

- Tenant_id and end date available - Will produce the message that please enter begin date.

- Tenant_id and begin date available - Will produce the message that please enter end date.

**Command-Line Input Example:**

```
python billing.py -t b284066db1b842208f989472991bbe73 -b '2015-12-25 00:00:00' -e '2015-12-25 15:00:00'
```

**Input details using Config File Example**

```

##########################
## Connection Configuration
##########################

# Provide the connection details
[connection]
tenant_name=demo
auth_url=http://127.0.0.1:5000/v2.0
username=admin
password=sop52maw

# Details for fetching the billing data
# provide tenant_id, begin date and end date
# date format ex: 2015-12-25 15:00:00
[billing_details]
tenant_id=bb16e60a427941fbb27bc2d055b9749a
begin=2016-01-05 00:00:00
end=2016-01-15 15:00:00
```

But in any case details for **[connection]** section should be provided clearly.

**Note:**

We need to setup the cloudkitty with ceilometer enabled.
Need to utilize the devstack.cloudscript for the same.

https://github.com/nephoscale/openstack-tools/blob/master/devstack.cloudscript

Part of codes which will enable the ceilometer and cloudkitty

```
enable_plugin ceilometer https://github.com/muraliselva10/ceilometer.git master
ENABLED_SERVICES+=,horizon
enable_plugin cloudkitty https://github.com/stackforge/cloudkitty master
ENABLED_SERVICES+=,ck-api,ck-proc
```

Following part of codes were needs to be edited as per our requirement:

```
# For activating necessary services
# we can modify period of report
[[post-config|$CLOUDKITTY_CONF]]
[collect]
period = 300
services=compute,image,volume,network.bw.in,network.bw.out,network.floating
EOF
```

As well as configuration of rating should have done already.

https://github.com/nephoscale/openstack-tools/tree/master/rate_tool
