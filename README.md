storpool-charms - deploy the StorPool OpenStack integration Juju charms
=======================================================================

Overview
--------

The `storpool-charms` tool is used to deploy the Juju charms needed for
the StorPool integration with the OpenStack charms bundle.


Deploying pre-built charms
--------------------------

The fastest way to get the StorPool charms up and running is to use one of
the pre-packaged versions uploaded [as releases to the GitHub repository.][releases]
Once the release archive has been downloaded and extracted, change into
the newly-created `storpool-charms-<YYYYMMDD>-<series>` directory and run:

    ./storpool-charms.py deploy

Make sure that you do this from a shell that has been properly set up for
access to the Juju cluster; the easiest way to test this is to run
the `juju status` command beforehand and check that it displays the correct
machines, applications, and units.  If the StorPool charms have previously been
installed on the Juju cluster, then `./storpool-charms.py undeploy` will need to
be executed first.

After the charms have been deployed to the Juju cluster, they will still need
to be configured; please [contact StorPool][support] for information about
the charms configuration.


Building the charms
-------------------

To get the latest version of the StorPool charms, follow this procedure.

1. Check out the `storpool-charms` tool from its GitHub repository:

    `git clone https://github.com/storpool/storpool-charms.git`

    `cd storpool-charms`

2. Check out the current version of the charms:

    `./storpool-charms.py checkout`

3. Build the charms (make sure the `charm-tools` Ubuntu package is installed):

    `./storpool-charms.py build`

4. Deploy the newly-built charms:

    `./storpool-charms.py deploy`

5. At a later point, fetch the latest StorPool updates from the GitHub repositories:

    `./storpool-charms.py pull && ./storpool-charms.py build`


Contact us
----------

Please feel free to [contact StorPool][support] for any additional information or
for assistance with any problems.


[releases]: https://github.com/storpool/storpool-charms/releases
[support]: mailto:support@storpool.com
