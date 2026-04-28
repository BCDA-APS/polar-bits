id4_common.utils.device_loader
==============================

.. py:module:: id4_common.utils.device_loader






Module Contents
---------------

.. py:data:: logger

.. py:data:: DEFAULT_FILE

.. py:data:: MAIN_NAMESPACE
   :value: '__main__'


.. py:function:: load_yaml_devices(file=DEFAULT_FILE)

   Load devices from a YAML configuration file.

   :param file: The path to the YAML configuration file. Defaults to `DEFAULT_FILE`.
   :type file: str or pathlib.Path, optional

   :returns: A dictionary where keys are device names and values are dictionaries
             containing device parameters, including the class of the device.
   :rtype: dict

   .. rubric:: Notes

   The YAML file is expected to have a structure where each key represents
   a device class, and its value is a list of device parameters. Each device
   must have a 'name' parameter which is used as the key in the returned
   dictionary.


.. py:data:: AVAILABLE_DEVICES

.. py:function:: find_loadable_devices(name=None, label=None, exact_name=False)

   Find devices based on name and label search.

   :param name: The name of the device to search for. If None, all devices are
                considered.
   :type name: str, optional
   :param label: The label to search for within device labels. If None, all labels are
                 considered.
   :type label: str, optional
   :param exact_name: If True, perform an exact match on the device name. If False, perform a
                      partial match. Defaults to False.
   :type exact_name: bool, optional

   :returns: Prints a table of devices matching the search criteria in
             reStructuredText format.
   :rtype: None

   .. rubric:: Notes

   The function filters devices from `AVAILABLE_DEVICES` based on the provided
   `name` and `label`. It uses `_exact` or `_partial` functions for name
   matching based on the `exact_name` parameter. The filtered devices are
   displayed in a table format with columns for Name, Prefix, and Labels.


.. py:function:: connect_device(device, baseline=None, raise_error=True)

   Connects a device and optionally adds it to the baseline.

   :param device: The device object to be connected. It must have a `name` attribute
                  and a `wait_for_connection` method.
   :type device: object
   :param baseline: Determines if the device should be added to the baseline. If None,
                    the function checks the device's labels in `AVAILABLE_DEVICES` to
                    decide. Defaults to None.
   :type baseline: bool or None, optional
   :param raise_error: If raise_error is True, a ValueError is raised if the device is not
                       found in `AVAILABLE_DEVICES`.
   :type raise_error: bool, optional

   :raises ValueError: If the device is not found in `AVAILABLE_DEVICES` and `baseline` is
       None.

   .. rubric:: Notes

   The function first checks if the device is already registered in
   `oregistry`. If so, it removes the existing entry. It then attempts to
   connect the device and apply default settings if available. The device is
   registered in `oregistry` and added to the baseline if applicable. If a
   `TimeoutError` occurs during connection, the device is removed from
   `oregistry` and the baseline.


.. py:function:: load_device(name, file=None)

   Load and connect a device by its name from a YAML configuration file.

   :param name: The name of the device to be loaded.
   :type name: str
   :param file: The path to the YAML configuration file. If None, the default
                configuration file is used.
   :type file: str or None, optional

   :raises ValueError: If the device is not found in the configuration file or if the
       device class is not specified in the YAML file.

   .. rubric:: Notes

   The function checks if the device already exists in the registry.
   If not, it loads the device configuration, dynamically imports the
   device class, and connects the device. The device is then added to
   the main namespace and optionally to the baseline if specified in
   the configuration.


.. py:function:: AD_plugin_primed(plugin)

   Determine whether an AreaDetector plugin is primed.

   This variant treats a time stamp of 0 as unprimed.

   :param plugin: The plugin device. Expected to provide:
                  - time_stamp: A signal-like object with a .get() method that returns
                    a numeric time stamp.
   :type plugin: object

   :returns: True if the plugin appears primed (time stamp != 0), False otherwise.
   :rtype: bool

   .. rubric:: Notes

   This is a modification of the APS AD_plugin_primed heuristic. Using
   time_stamp == 0 to indicate an unprimed state may not be generic across
   all detectors.


.. py:function:: AD_prime_plugin2(plugin)

   Prime (warm up) the HDF5 AreaDetector plugin if it is not already primed.

   This function checks whether the given plugin has been primed using
   AD_plugin_primed. If the plugin is not primed, it attempts to call the
   plugin's warmup method when available. If no warmup method is present,
   a warning is logged to indicate that manual warmup may be required.

   :param plugin: The AreaDetector plugin device to prime. Expected to have:
                  - name (str): Plugin name for logging.
                  - time_stamp (Signal-like): Used by AD_plugin_primed to determine
                    primed state.
                  - warmup (callable, optional): Method that performs the warmup.
   :type plugin: object

   :rtype: None

   .. rubric:: Notes

   - Determination of the primed state is delegated to
     AD_plugin_primed(plugin). For some detectors (e.g., Vortex), a timestamp
     of 0 is treated as "unprimed."
   - If the plugin is already primed, this function logs at debug level and
     returns without performing any action.


.. py:function:: reload_all_devices(file='devices.yml', stations=None)

   Reload all devices from a configuration file and connect devices.

   :param file: Path to the YAML devices configuration file. Defaults to "devices.yml".
   :type file: str, optional
   :param stations: List of station labels to connect after reloading. If None, connects
                    all stations: ["core", "4idb", "4idg", "4idh"].
   :type stations: list of str, optional

   :returns: Creates devices and add them to the main namespace
   :rtype: None

   .. rubric:: Notes

   This function:
   1. Invokes the `make_devices` plan with `clear=True` via the RunEngine to
      rebuild and register devices from the specified configuration file.
   2. Searches the registry for devices matching the given station labels
      and attempts to connect them without raising errors on failure.


.. py:function:: remove_device(device)

   Remove a device from the registry and the baseline list.

   :param device: The device instance to remove, or the registered name of the device.
   :type device: OphydObject or str

   :rtype: None

   :raises ValueError: If `device` is neither an OphydObject nor a string, or if a device
       name is provided but no matching device is found in the registry.

   .. rubric:: Notes

   If a device name (str) is provided, the function looks up the device in
   `oregistry`. The device is removed from `oregistry` and, if present, from
   `sd.baseline`.
