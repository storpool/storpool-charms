storpool-charms-manage - deploy the StorPool OpenStack integration Juju charms
==============================================================================

Overview
--------

The `storpool-charms-manage` package and the `spcharms_manage` tool are
used to deploy the Juju charms needed for the StorPool integration with
the OpenStack charms bundle.


Deploying pre-built charms
--------------------------

The fastest way to get the StorPool charms up and running is to use one of
the pre-packaged versions uploaded [as releases to the GitHub repository.][releases]
Once the release archive has been downloaded and extracted, change into
the newly-created `storpool-charms-<YYYYMMDD>-<series>` directory and run:

    spcharms_manage deploy

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

1. Check out the current version of the charms:

    `spcharms_manage.py checkout`

2. Build the charms (make sure the `charm-tools` Ubuntu package is installed):

    `spcharms_manage.py build`

3. Deploy the newly-built charms:

    `spcharms_manage.py deploy`

4. At a later point, fetch the latest StorPool updates from the GitHub repositories:

    `spcharms_manage.py pull && spcharms_manage.py build`


Using the storpool.charms.manage modules
----------------------------------------

The modules in the storpool.charms.manage namespace may be used by Python
programs not only to build and deploy the StorPool charms, but also to
configure them, even if they have been deployed in a different way, taking
into account the current deployment of the OpenStack charms in a Juju
cluster.  The `storpool.charms.manage.juju` module's
`get_storpool_config_data()` and `get_charm_config_data()` functions will
provide dictionaries with values that may later be incorporated into
text or YAML configuration snippets:

    from storpool.charms.manage import config as sconfig
    from storpool.charms.manage import juju as sjuju

    cfg = sconfig.Config(space='storpool', repo_auth='username:password')
    status = sjuju.get_status(cfg)

    spcfg = sjuju.get_storpool_config_data(cfg, status)
    for hostname, data in spcfg.items():
        print('Host {name}: StorPool ID {oid}'
              .format(name=hostname, oid=data['SP_OURID']))

    charmcfg = sjuju.get_charm_config_data(cfg, status, spcfg, [])

The storpool.charms.manage modules are fully typed.

Contact us
----------

Please feel free to [contact StorPool][support] for any additional information or
for assistance with any problems.


[releases]: https://github.com/storpool/storpool-charms/releases
[support]: mailto:support@storpool.com
