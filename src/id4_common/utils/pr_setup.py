"""Polarization-ratio (PR) scan setup utilities."""

__all__ = ["pr_setup"]

from apsbits.core.instrument_init import oregistry

from ..callbacks.dichro_stream import plot_dichro_settings


class PRSetup:
    positioner = None
    offset = None
    oscillate_pzt = True
    _dichro_steps = [1, -1, -1, 1]

    @property
    def dichro_steps(self):
        return self._dichro_steps

    @dichro_steps.setter
    def dichro_steps(self, value):
        self._dichro_steps = value
        plot_dichro_settings.settings.pattern = value

    @property
    def available_prs(self):
        prs = oregistry.findall("phase retarder", alow_none=True)
        if prs is None:
            raise ValueError("No phase retarder was found!")
        prs.sort(key=lambda x: x.name)
        return prs

    def __init__(self):
        self._current_setup = {}

    def __repr__(self):
        tracked = ""
        for pr in oregistry.findall("phase retarder"):
            if pr.tracking.get():
                tracked += f"{pr.name} "

        oscillate = self.positioner.name if self.positioner else "None"
        offset = self.offset.name if self.offset else "None"
        try:
            pzt_center = self.offset.parent.center.get()
        except AttributeError:
            pzt_center = "None"

        return (
            "Phase retarder settings\n"
            f"  Tracking PRs = {tracked}\n"
            f"  Oscillating PR = {oscillate}\n"
            f"  Offset positioner = {offset}\n"
            f"  Offset value = {self.offset.get()}\n"
            f"  PZT center = {pzt_center}\n"
            f"  Steps for dichro scan = {self.dichro_steps}\n"
        )

    def _get_setup(self, pr):
        _setup = {}

        if self.positioner is not None:
            # Positioner is pr.th (parent=pr) or pr.pzt.localdc (parent.parent=pr).
            try:
                oscillates = (
                    self.positioner.parent is pr
                    or self.positioner.parent.parent is pr
                )
            except AttributeError:
                oscillates = False
            _setup["oscillate"] = "yes" if oscillates else "no"
            _setup["method"] = "pzt" if self.oscillate_pzt else "motor"
        else:
            # No positioner set yet — use stored per-PR history if available.
            saved = self._current_setup.get(pr.name, {})
            _setup["oscillate"] = saved.get("oscillate", "no")
            _setup["method"] = saved.get("method", "pzt")

        _setup["offset"] = pr.pzt.offset_degrees.get()
        _setup["center"] = pr.pzt.center.get()

        return _setup

    def __str__(self):
        return self.__repr__()

    def __call__(self):
        print("Setup of the phase retarders for dichro scans.")
        print("Note that you can only oscillate one phase retarder stack.")

        _positioner = None

        # Transmission check
        while True:
            _default = (
                "yes" if plot_dichro_settings.settings.transmission else "no"
            )
            trans = (
                input(f"Are you measuring in transmission? ({_default}): ")
                or _default
            )
            if trans.lower() == "yes":
                plot_dichro_settings.settings.transmission = True
                break
            elif trans.lower() == "no":
                plot_dichro_settings.settings.transmission = False
                break
            else:
                print("Invalid answer, it must be yes or no.")

        # Cycle through the PRs
        for pr in self.available_prs:
            print(" ++ {} ++ ".format(pr.name.upper()))

            # Track the energy?
            while True:
                track = "yes" if pr.tracking.get() else "no"
                track = input(f"\tTrack? ({track}): ") or track

                if track.lower() == "yes":
                    pr.tracking.put(True)
                    break
                elif track.lower() == "no":
                    pr.tracking.put(False)
                    break
                else:
                    print("Only yes or no are acceptable answers.")

            # If no positioner has been selected to oscillate, we will ask.
            # This assumes that we only oscillate one PR, which is tracked.
            if _positioner is None and track == "yes":
                setup = self._get_setup(pr)
                # Oscillate this PR?
                while True:
                    oscillate = (
                        input(f"\tOscillate? ({setup['oscillate']}): ")
                        or setup["oscillate"]
                    )
                    # If this will oscillate, need to determine the positioner
                    # to use and its parameters.
                    if oscillate.lower() == "yes":
                        # PR3 doesn't have a PZT.
                        if pr.name == "pr3":
                            method = "motor"
                            _positioner = pr.th
                        else:
                            while True:
                                method = (
                                    input(
                                        f"\tUse motor or PZT? ({setup['method']}): "
                                    )
                                    or setup["method"]
                                )
                                if method.lower() == "motor":
                                    _positioner = pr.th
                                    break
                                elif method.lower() == "pzt":
                                    _positioner = pr.pzt.localdc
                                    break
                                else:
                                    print(
                                        "Only motor or pzt are acceptable answers."
                                    )
                        # Get offset
                        while True:
                            try:
                                offset = (
                                    input(
                                        f"\tOffset (in degrees) ({setup['offset']}): "
                                    )
                                    or setup["offset"]
                                )
                                _positioner.parent.offset_degrees.put(
                                    float(offset)
                                )
                                break
                            except ValueError:
                                print("Must be a number.")

                        # if PZT is used, then get the center.
                        if method.lower() == "pzt":
                            self.oscillate_pzt = True
                            # Get offset signal
                            self.offset = _positioner.parent.offset_microns
                            # Get the PZT center.
                            while True:
                                try:
                                    center = (
                                        input(
                                            "\tPZT center in microns "
                                            f"({setup['center']}): "
                                        )
                                        or setup["center"]
                                    )
                                    _positioner.parent.center.put(float(center))
                                    break
                                except ValueError:
                                    print("Must be a number.")
                        else:
                            self.oscillate_pzt = False
                            # Get offset signal
                            self.offset = _positioner.parent.offset_degrees

                        self._current_setup[pr.name] = {
                            "oscillate": "yes",
                            "method": method.lower(),
                        }
                        break
                    elif oscillate.lower() == "no":
                        self._current_setup[pr.name] = {
                            "oscillate": "no",
                            "method": setup["method"],
                        }
                        break
                    else:
                        print("Only yes or no are acceptable answers.")

            else:
                if _positioner and track == "yes":
                    print(
                        f"\tYou already selected {_positioner.name} to oscillate."
                    )

        self.positioner = _positioner


pr_setup = PRSetup()
pr_setup.dichro_steps = [1, -1, -1, 1]
