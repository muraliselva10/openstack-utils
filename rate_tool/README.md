# Cloudkitty-pricing-automation

This is the script which helps us to configure the Cloudkitty pricing in automated way.

Using this you can be able to configure pricing based on the following Heads.

- Pricing based on instance size (m1.tiny, m1.small etc.,).

- Pricing based on the Image selected.

- Pricing based on the Network inbound data.

- Pricing based on the Network outbound data.

- Pricing for the floating IP used.

What you need to do is simply edit the cloudkitty_pricing.config file with necessary details.

Consider our config file is having content is as follows:

```
[connection]
tenant_name=admin
auth_url=http://127.0.0.1:5000/v2.0
username=admin
password=sop52maw

[instance_size_section]
m1.tiny=1.5
m1.small=2.5
m1.medium=3.5
m1.large=4.5
m1.xlarge=5.5


[image_section]
591c008a-6833-4167-9749-e5e5a74d1de4=7.5
sdfe008a-6833-4167-9749-e5e5a74d1de4=8.5
```

So in the above section you need to edit the necessary portions.

**[connection]** section is responsible for configuring the connection here as needed.
Edit the necessary details here such as 'tenant_name', 'auth_url', 'username', 'password'.


**[instance_size_section]** is responsible for configuration of price based on the instance size.
For example m1.tiny, m1.small etc will be the instance size which needs to be created.
So we can edit the price value as needed for configuring the same.
This is an Cost for the certain period which we mentioned in an cloudkitty.conf file.

```
m1.tiny=1.5
```
We can edit the value as needed(2.5, 3.5 etc)


**[image_section]** is responsible for configuration of price based on the image provided.
This is an Cost for the certain period which we mentioned in an cloudkitty.conf file.
We need to take the image id from the devstack admin panel and provide it here with the cost as follows:

```
591c008a-6833-4167-9749-e5e5a74d1de4=7.5
```

We can be able to provide 'n' number of image id's here to configure pricing.

**[floating_ip]** is responsible for configuration of cost for each floating IP used.
We need to simply enter the rate for the each floating IP, Which is an one time fee for the floating IP.
Sample for the same is as follows:

```
cost_floating_ip=4.5
```


**[network_inbound]** is responsible for configuration of cost for network.inbound transfers.
We need to simply enter the rate for the network inbound data, Which is for the MB of data consumed for the period we defined in the cloudkitty.conf file.

```
cost_network_inbound=9.5
```

**[network_outbound]** is responsible for configuration of cost for network.inbound transfers.
We need to simply enter the rate for the network outbound data, Which is for the MB of data consumed for the period we defined in the cloudkitty.conf file.

```
cost_network_outbound=9.5
```

**Pricing Logic and sample results**:

We are applying flat pricing logic here.

Consider instance size is having price as follows 1.5,2.5,3.5,4.5,5.5 for sizes m1.tiny,m1.small,m1.medium,m1.large,m1.xlarge respectively.

Image "cirros-0.3.4-x86_64-uec" is assigned a value of 7.5 and image "Windows server" is assigned a value of 8.5.

Note: In config file you will be defining only the image UUID and cost, not Image name as demonstrated here.

Now you are selecting the size as m1.small and image "cirros-0.3.4-x86_64-uec".

So result will be 2.5 + 7.5 = 10.0.


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
