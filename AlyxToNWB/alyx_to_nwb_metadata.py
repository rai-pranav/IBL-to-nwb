import re
import json
from oneibl.one import ONE
from .schema import metafile as nwb_schema


class Alyx2NWBMetadata:
    # TODO: add docstrings

    def __init__(self, eid=None, one_obj=None, **one_search_kwargs):
        if not one_obj:
            self._one_obj = one_obj
        else:
            self.one_obj = ONE()
        if not eid:
            eid = self.one_obj.search(**one_search_kwargs)
            if len(eid) > 1:
                print(f'nos of EIDs found: {len(eid)}, generating metadata from all')
                if input('continue? y/n') == 'y':
                    pass
                else:
                    exit()
        self.one_search_kwargs = one_search_kwargs
        self.schema = nwb_schema
        self.one_obj = one_obj
        if not one_obj:
            self.one_obj = ONE()
        elif not isinstance(one_obj, ONE):
            raise Exception('one_obj is not of ONE class')
        self.dataset_description_list = self._get_dataset_details()
        self.eid_list = self._get_eid_list(eid)
        self.eid_session_info = self._retrieve_eid_endpoint()
        self.dataset_type_list = self._list_eid_metadata('dataset_type')
        self.users_list = self._list_eid_metadata('users')
        self.subjects_list = self._list_eid_metadata('subjects')
        self.labs_list = self._list_eid_metadata('labs')
        self.dataset_details, self.dataset_simple = self._dataset_type_parse()
        self._get_lab_table()
        self._get_subject_table()

    def _get_eid_list(self, eid_list):
        if eid_list:
            if not isinstance(eid_list, list):
                eid_list = [eid_list]
        else:
            eid_list = self._one_obj.search(**self.one_search_kwargs)
        return eid_list

    def _get_dataset_details(self):
        """
        Retrieves all datasets in the alyx database currently.
        Retrieves a list of dicts with keys like id, name, created_by,description etc. Uses only name and description.
        Returns
        -------
        list
            List of dicts:
            {<dataset-name> : <dataset_description>
        """
        data_url_resp = self.one_obj.alyx.rest('dataset-types', 'list')
        out_dict = dict()
        for i in data_url_resp:
            out_dict.update({i['name']: i['description']})
        return out_dict

    def _list_eid_metadata(self, list_type):
        """
        Uses one's list method to get the types of <list_type> data from the given eid.
        Parameters
        ----------
        list_type: str
            one of strings from
            >>> ONE().search_terms()
        Returns
        -------
        list
        """
        list_type_returned = [None]*len(self.eid_list)
        for val, e_id in enumerate(self.eid_list):
            list_type_returned[val] = self.one_obj.list(e_id, list_type)
        return list_type_returned

    def _retrieve_eid_endpoint(self):
        """
        To get the current sessions url response. Contains all the session metadata as well as the current datasets etc.
        Returns
        -------
        list
            list of server responses.
        """
        eid_sess_info = [None]*len(self.eid_list)
        for val, ceid in enumerate(self.eid_list):
            eid_sess_info[val] = self.one_obj.alyx.rest('sessions/' + ceid, 'list')
            for i in eid_sess_info[val]:
                if eid_sess_info[val][i] == None:
                    eid_sess_info[val][i] = 'None'
        return eid_sess_info

    def _get_lab_table(self):
        self.lab_table = self.one_obj.alyx.rest('labs', 'list')

    def _get_subject_table(self):
        self.subject_table = [dict()]*len(self.eid_list)
        for val, e_id in enumerate(self.eid_list):
            self.subject_table[val] = self.one_obj.alyx.rest('subjects/' + self.eid_session_info[val]['subject'],
                                                             'list')

    def _dataset_type_parse(self):
        """

        Returns
        -------
        list
            list of dicts:
            {<dataset object name>: (eg. spikes, clusters etc)
                [
                    {name: objects attribute type (eg. times, intervals etc
                    description: attributes description}
                    {name: objects attribute type (eg. times, intervals etc
                    description: attributes description}
                ]
            }
        """
        dataset_type_list = [None]*len(self.eid_list)
        dataset_type_list_simple = [None]*len(self.eid_list)
        for val, Ceid in enumerate(self.eid_list):
            split_list_objects = [i.split('.')[0] for i in self.dataset_type_list[val]]
            split_list_attributes = [i.split('.')[1] for i in self.dataset_type_list[val]]
            dataset_description = [self.dataset_description_list[i] for i in self.dataset_type_list[val]]
            split_list_objects_dict_details = dict()
            split_list_objects_dict = dict()
            for obj in set(split_list_objects):
                split_list_objects_dict_details[obj] = []
                split_list_objects_dict[obj] = []
            for att_idx, attrs in enumerate(split_list_attributes):
                append_dict = {'name': attrs,
                               'description': dataset_description[att_idx]}
                # 'extension': dataset_extension[att_idx] }
                split_list_objects_dict_details[split_list_objects[att_idx]].extend([append_dict])
                split_list_objects_dict[split_list_objects[att_idx]].extend([attrs])
            dataset_type_list[val] = split_list_objects_dict_details
            dataset_type_list_simple[val] = split_list_objects_dict
        return dataset_type_list, dataset_type_list_simple

    @staticmethod
    def _unpack_dataset_details(dataset_details, object_name, custom_attrs=None, match_str=' '):
        """
        helper function to split object and attributes of the IBL datatypes into
        names: obj_attr; data= obj.attr; desc for each
        :param dataset_details:
        :param object_name:
        :param custom_attrs:
        :param match_str:
        :return:
        """
        cond = lambda x: re.match(match_str, x)
        datafiles_all = [object_name + '.' + ii['name'] for ii in dataset_details[object_name] if not cond(ii['name'])]
        datafiles_names_all = [ii['name'] for ii in dataset_details[object_name] if
                               not cond(ii['name'])]
        datafiles_desc_all = [ii['description'] for ii in dataset_details[object_name] if not cond(ii['name'])]
        if custom_attrs:
            datafiles_inc = [i for i in datafiles_all if i in object_name + '.' + custom_attrs]
            datafiles_names_inc = [datafiles_names_all[j] for j, i in enumerate(datafiles_all) if
                                   i in object_name + '.' + custom_attrs]
            datafiles_desc_inc = [datafiles_desc_all[j] for j, i in enumerate(datafiles_all) if
                                  i in object_name + '.' + custom_attrs]
        else:
            datafiles_inc = datafiles_all
            datafiles_names_inc = datafiles_names_all
            datafiles_desc_inc = datafiles_desc_all
        return datafiles_inc, datafiles_names_inc, datafiles_desc_inc

    def _initialize_container_dict(self, name=None, default_value=None):
        if default_value is None:
            default_value = dict()
        if name:
            outval = []
            for i in range(len(self.eid_list)):
                outval.extend([dict({name: default_value.copy()})])
            return outval
        else:
            return [None]*len(self.eid_list)

    def _get_all_object_names(self):
        outlist = [[]]*len(self.eid_list)
        for val, Ceid in enumerate(self.eid_list):
            outlist[val] = sorted(list(set([i.split('.')[0] for i in self.dataset_type_list[val]])))
        return outlist

    def _get_current_object_names(self, obj_list):
        out_list = []
        for val, Ceid in enumerate(self.eid_list):
            loop_list=[]
            for j, k in enumerate(obj_list):
                if k in self._get_all_object_names()[val]:
                    loop_list.extend([i for i in self._get_all_object_names()[val] if k == i])
            out_list.append(loop_list)
        return out_list

    def _get_timeseries_object(self, dataset_details, object_name, ts_name, custom_attrs=None, drop_attrs=None, **kwargs):
        """

        Parameters
        ----------
        dataset_details
            self.dataset_details
        object_name
            name of hte object_name in the IBL datatype
        ts_name
            the key name for the timeseries list
        custom_attrs
            Attributes to consider
        kwargs
            additional keys/values to add to the default timeseries. For derivatives of TimeSEries

        Returns
        -------
        dict()
            {
                "time_series": [
                    {
                      "name": "face_motionEnergy",
                      "data": "face.motionEnergy",
                      "timestamps": "face.timestamps",
                      "description": "Features extracted from the video of the frontal aspect of the subject, including the subject\\'s face and forearms."
                    },
                    {
                      "name": "_ibl_lickPiezo_times",
                      "data": "_ibl_lickPiezo.raw",
                      "timestamps": "_ibl_lickPiezo.timestamps",
                      "description": "Voltage values from a thin-film piezo connected to the lick spout, so that values are proportional to deflection of the spout and licks can be detected as peaks of the signal."
                    }
                ]
            }
        """
        matchstr = r'.*time.*|.*interval.*'
        timeattr_name = [i['name'] for i in dataset_details[object_name] if re.match(matchstr, i['name'])]
        dataset_details[object_name],_ = self._drop_attrs(dataset_details[object_name].copy(), drop_attrs)
        datafiles, datafiles_names, datafiles_desc = \
            self._unpack_dataset_details(dataset_details.copy(), object_name, custom_attrs, match_str=matchstr)
        datafiles_timedata, datafiles_time_name, datafiles_time_desc = \
            self._unpack_dataset_details(dataset_details.copy(), object_name, timeattr_name[0])
        if not datafiles:
            datafiles_names = datafiles_time_name
            datafiles_desc = datafiles_time_desc
            datafiles = ['None']
        timeseries_dict = {ts_name: [None]*len(datafiles)}
        for i, j in enumerate(datafiles):
            timeseries_dict[ts_name][i] = {'name': datafiles_names[i],
                                           'description': datafiles_desc[i],
                                           'timestamps': datafiles_timedata[0],
                                           'data': datafiles[i]}
            timeseries_dict[ts_name][i].update(**kwargs)
        return timeseries_dict

    @staticmethod
    def _attrnames_align(attrs_dict, custom_names):
        """
        the attributes that receive the custom names are reordered to be first in the list
        Parameters. This assigns description:'no_description' to those that are not found. This will
        later be used(nwb_converter) as an identifier for non-existent data for the given eid.
        ----------
        attrs_dict:list
            list of dict(attr_name:'',attr_description:'')
        custom_names
            same as 'default_colnames_dict' in self._get_dynamictable_object
        Returns
        -------
        dict()
        """
        attrs_list = [i['name'] for i in attrs_dict]
        out_dict = dict()
        out_list = []
        list_id_func_exclude = \
            lambda val, comp_list, comp_bool: [i for i, j in enumerate(comp_list) if comp_bool & (j == val)]
        cleanup = lambda x: [i[0] for i in x if i]
        if custom_names:
            custom_names_list = [i for i in list(custom_names.values())]
            custom_names_dict = []
            for i in range(len(custom_names_list)):
                custom_names_dict.extend([{'name':custom_names_list[i],'description': 'no_description'}])
            attr_list_include_idx = cleanup([list_id_func_exclude(i, attrs_list, True) for i in custom_names_list])
            attr_list_exclude_idx = set(range(len(attrs_list))).difference(set(attr_list_include_idx))
            custom_names_list_include_idx = [i for i,j in enumerate(custom_names_list) if list_id_func_exclude(j, attrs_list, True)]
            for ii,jj in enumerate(custom_names_list_include_idx):
                custom_names_dict[custom_names_list_include_idx[ii]] = attrs_dict[attr_list_include_idx[ii]]
                custom_names_list[custom_names_list_include_idx[ii]] = attrs_list[attr_list_include_idx[ii]]
            extend_dict = [attrs_dict[i] for i in attr_list_exclude_idx]
            extend_list = [attrs_list[i] for i in attr_list_exclude_idx]
            custom_names_dict.extend(extend_dict)
            custom_names_list.extend(extend_list)
            return custom_names_dict, custom_names_list
        else:
            out_dict = attrs_dict
            out_list = attrs_list
            return out_dict, out_list

    @staticmethod
    def _drop_attrs(dataset_details, drop_attrs, default_colnames_dict=None):
        """
        Used to remove given attributes of the IBL dataset.
        Parameters
        ----------
        dataset_details
        drop_attrs
        default_colnames_dict

        Returns
        -------

        """
        dataset_details_copy = dataset_details.copy()
        if drop_attrs is None:
            return dataset_details, default_colnames_dict
        elif not(default_colnames_dict==None):
            default_colnames_dict_copy = default_colnames_dict.copy()
            for i,j in default_colnames_dict_copy.items():
                if j in drop_attrs:
                    default_colnames_dict.pop(i)
        attrs_list = [i['name'] for i in dataset_details]
        for i, j in enumerate(attrs_list):
            if j in drop_attrs:
                del dataset_details_copy[i]
        return dataset_details_copy, default_colnames_dict

    @staticmethod
    def _get_dynamictable_array(**kwargs):
        """
        Helper to dynamictable object method
        Parameters
        ----------
        kwargs
            keys and values that define the dictionary,
            both keys and values are lists where each index would slice all the keys/values and create a dict out of that

        Returns
        -------
        list
            list of dictionaries each with the keys and values from kwargs

        """
        custom_keys = list(kwargs.keys())
        custom_data = list(kwargs.values())
        out_list = [None]*len(custom_data[0])
        for ii, jj in enumerate(custom_data[0]):
            out_list[ii] = dict().copy()
            for i, j in enumerate(custom_keys):
                out_list[ii][j] = custom_data[i][ii]
        return out_list

    def _get_dynamictable_object(self, dataset_details, object_name, dt_name, default_colnames_dict=None,
                                 custom_attrs=None,drop_attrs=None):
        """

        Parameters
        ----------
        dataset_details
            self.dataset_details for each eid
        object_name:str
            object from the IBL data types from which to create this table.
        dt_name:str
            custom name for the dynamic table. Its the key with the value being dynamictable_array
        default_colnames_dict:dict()
            keys are the custom names of the columns, corresponding values are the attributes which have to be renamed.
        custom_attrs:list
            list of attributes for the given IBL object in object_name to be considered, all others are ignored

        Returns
        -------
        outdict:dict()
            example output below:
            {'Trials':
                    [
                        {
                          "name": "column1 name",
                          "data": "column data uri (string)",
                          "description": "col1 description"
                        },
                        {
                           "name": "column2 name",
                          "data": "column data uri (string)",
                          "description": "col2 description"
                        }
                    ]
                }
        """
        dataset_details[object_name], default_colnames_dict = self._drop_attrs(dataset_details[object_name].copy(),
                                                                drop_attrs, default_colnames_dict)
        dataset_details[object_name], _ = self._attrnames_align(dataset_details[object_name].copy(), default_colnames_dict)
        if not default_colnames_dict:
            default_colnames = []
        else:
            default_colnames = list(default_colnames_dict.keys())
        custom_columns_datafilename, custom_columns_name, custom_columns_description = \
            self._unpack_dataset_details(dataset_details.copy(), object_name, custom_attrs)
        custom_columns_name[:len(default_colnames)] = default_colnames
        in_list = self._get_dynamictable_array(
            name=custom_columns_name,
            data=custom_columns_datafilename,
            description=custom_columns_description)
        outdict = {dt_name: in_list}
        return outdict

    @property
    def eid_metadata(self):
        eid_metadata = [None]*len(self.eid_list)
        for val, Ceid in enumerate(self.eid_list):
            eid_metadata[val] = dict(eid=self.eid_list[val])
        return eid_metadata

    @property
    def nwbfile_metadata(self):
        nwbfile_metadata_dict = self._initialize_container_dict('NWBFile')
        for val, Ceid in enumerate(self.eid_list):
            nwbfile_metadata_dict[val]['NWBFile']['session_start_time'] = self.eid_session_info[val]['start_time']
            nwbfile_metadata_dict[val]['NWBFile']['keywords'] = [','.join(self.eid_session_info[val]['users']),
                                                                 self.eid_session_info[val]['lab'], 'IBL']
            nwbfile_metadata_dict[val]['NWBFile']['experiment_description'] = self.eid_session_info[val]['narrative']
            nwbfile_metadata_dict[val]['NWBFile']['session_id'] = Ceid
            nwbfile_metadata_dict[val]['NWBFile']['experimenter'] = self.eid_session_info[val]['users']
            nwbfile_metadata_dict[val]['NWBFile']['identifier'] = Ceid
            nwbfile_metadata_dict[val]['NWBFile']['institution'] = \
                [i['institution'] for i in self.lab_table if i['name'] == [self.eid_session_info[val]['lab']][0]][0]
            nwbfile_metadata_dict[val]['NWBFile']['lab'] = self.eid_session_info[val]['lab']
            nwbfile_metadata_dict[val]['NWBFile']['session_description'] = self.eid_session_info[val]['task_protocol']
            nwbfile_metadata_dict[val]['NWBFile']['surgery'] = 'None'
            nwbfile_metadata_dict[val]['NWBFile']['notes'] = 'Procedures:' + ','.join(
                self.eid_session_info[val]['procedures']) \
                                                             + ', Project:' + self.eid_session_info[val]['project']

        return nwbfile_metadata_dict

    @property
    def subject_metadata(self):
        subject_metadata_dict = self._initialize_container_dict('Subject')
        for val, Ceid in enumerate(self.eid_list):
            if self.subject_table[val]:
                subject_metadata_dict[val]['Subject']['subject_id'] = self.subject_table[val]['id']
                subject_metadata_dict[val]['Subject']['description'] = self.subject_table[val]['description']
                subject_metadata_dict[val]['Subject']['genotype'] = ','.join(self.subject_table[val]['genotype'])
                subject_metadata_dict[val]['Subject']['sex'] = self.subject_table[val]['sex']
                subject_metadata_dict[val]['Subject']['species'] = self.subject_table[val]['species']
                subject_metadata_dict[val]['Subject']['weight'] = str(self.subject_table[val]['reference_weight'])
                subject_metadata_dict[val]['Subject']['date_of_birth'] = self.subject_table[val]['birth_date']
        return subject_metadata_dict

    @property
    def surgery_metadata(self):  # currently not exposed by api
        surgery_metadata_dict = [dict()]*len(self.eid_list)
        return surgery_metadata_dict

    @property
    def behavior_metadata(self):
        behavior_metadata_dict = self._initialize_container_dict('Behavior')
        behavior_objects = ['wheel', 'wheelMoves', 'licks', 'lickPiezo', 'face', 'eye']
        current_behavior_objects = self._get_current_object_names(behavior_objects)
        for val, Ceid in enumerate(self.eid_list):
            for k, u in enumerate(current_behavior_objects[val]):
                if 'wheel' in u:
                    behavior_metadata_dict[val]['Behavior']['BehavioralTimeSeries'] = \
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')
                if 'wheelMoves' in self.dataset_details[val].keys():
                    behavior_metadata_dict[val]['Behavior']['BehavioralEpochs'] = \
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'interval_series')
                if 'lickPiezo' in self.dataset_details[val].keys():
                    behavior_metadata_dict[val]['Behavior']['BehavioralTimeSeries']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
                if 'licks' in self.dataset_details[val].keys():
                    behavior_metadata_dict[val]['Behavior']['BehavioralEvents'] = \
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')
                if 'face' in self.dataset_details[val].keys():
                    behavior_metadata_dict[val]['Behavior']['BehavioralTimeSeries']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
                if 'eye' in self.dataset_details[val].keys():
                    behavior_metadata_dict[val]['Behavior']['PupilTracking'] = \
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')
        return behavior_metadata_dict

    @property
    def trials_metadata(self):
        trials_metadata_dict = self._initialize_container_dict('Trials')
        trials_objects = ['trials']
        current_trial_objects = self._get_current_object_names(trials_objects)
        for val, Ceid in enumerate(self.eid_list):
            for k, u in enumerate(current_trial_objects[val]):
                if 'trial' in u:
                    trials_metadata_dict[val] = self._get_dynamictable_object(self.dataset_details[val].copy(), 'trials',
                                                                              'Trials',
                                                                              default_colnames_dict=dict(
                                                                                  start_time='intervals',
                                                                                  stop_time='intervals'))
        return trials_metadata_dict

    @property
    def stimulus_metadata(self):
        stimulus_objects = ['sparseNoise', 'passiveBeeps', 'passiveValveClick', 'passiveVisual', 'passiveWhiteNoise']
        stimulus_metadata_dict = self._initialize_container_dict('Stimulus')
        current_stimulus_objects = self._get_current_object_names(stimulus_objects)
        for val, Ceid in enumerate(self.eid_list):
            for k, u in enumerate(current_stimulus_objects[val]):
                if 'sparseNoise' in u:
                    stimulus_metadata_dict[val]['Stimulus'] = \
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')
                if 'passiveBeeps' in u:
                    stimulus_metadata_dict[val]['Stimulus']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
                if 'passiveValveClick' in u:
                    stimulus_metadata_dict[val]['Stimulus']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
                if 'passiveVisual' in u:
                    stimulus_metadata_dict[val]['Stimulus']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
                if 'passiveWhiteNoise' in u:
                    stimulus_metadata_dict[val]['Stimulus']['time_series'].extend(
                        self._get_timeseries_object(self.dataset_details[val].copy(), u, 'time_series')['time_series'])
        return stimulus_metadata_dict

    @property
    def device_metadata(self):
        device_objects = ['probes']
        device_metadata_dict = self._initialize_container_dict('Device', default_value=[])
        current_device_objects = self._get_current_object_names(device_objects)
        for val, Ceid in enumerate(self.eid_list):
            for k, u in enumerate(current_device_objects[val]):
                for ii in range(2):
                    device_metadata_dict[val]['Device'].extend(
                        self._get_dynamictable_array(name=[f'{u}{ii}'],
                                                     description=['NeuroPixels probe'])
                    )
        return device_metadata_dict

    @property
    def units_metadata(self):
        units_objects = ['clusters', 'spikes']
        metrics_columns = ['cluster_id', 'cluster_id.1', 'num_spikes', 'firing_rate', 'presence_ratio',
                           'presence_ratio_std', 'isi_viol', 'amplitude_cutoff', 'amplitude_std', 'epoch_name',
                           'ks2_contamination_pct', 'ks2_label']

        units_metadata_dict = self._initialize_container_dict('Units')
        current_units_objects = self._get_current_object_names(units_objects)
        temp_dataset = self.dataset_details.copy()
        for val, Ceid in enumerate(self.eid_list):
            for k, u in enumerate(current_units_objects[val]):
                if 'clusters' in u:
                    units_metadata_dict[val] = \
                        self._get_dynamictable_object(self.dataset_details[val].copy(), 'clusters', 'Units',
                                                      default_colnames_dict=dict(location='brainAcronyms',
                                                                                 id='metrics',
                                                                                 waveform_mean='waveforms',
                                                                                 electrodes='channels',
                                                                                 electrode_group='probes',
                                                                                 ),
                                                      drop_attrs=['uuids'])
                    units_metadata_dict[val]['Units'].extend(
                        self._get_dynamictable_array(name=['obs_intervals', 'spike_times'],
                                                     data=['trials.intervals', 'spikes.clusters,spikes.times'],
                                                     description=['time intervals of each cluster',
                                                                  'spike times of cluster']
                                                     ))
                    units_metadata_dict[val]['Units'].extend(
                        self._get_dynamictable_array(name=metrics_columns,
                                                     data=['clusters.metrics']*len(metrics_columns),
                                                     description=['metrics_table columns data']*len(metrics_columns)
                                                     ))
        return units_metadata_dict

    @property
    def electrodegroup_metadata(self):
        electrodes_group_metadata_dict = self._initialize_container_dict('ElectrodeGroup', default_value=[])
        for val, Ceid in enumerate(self.eid_list):
            for ii in range(2):
                electrodes_group_metadata_dict[val]['ElectrodeGroup'].extend(
                    self._get_dynamictable_array(name=[f'Probe{ii}'],
                                                 description=['NeuroPixels device'],
                                                 device=[self.device_metadata[val]['Device'][ii]['name']],
                                                 location=[''])
                )
        return electrodes_group_metadata_dict

    @property
    def electrodetable_metadata(self):
        electrodes_objects = ['channels']
        electrodes_table_metadata_dict = self._initialize_container_dict()
        current_electrodes_objects = self._get_current_object_names(electrodes_objects)
        for val, Ceid in enumerate(self.eid_list):
            for i in current_electrodes_objects[val]:
                electrodes_table_metadata_dict[val] = self._get_dynamictable_object(
                    self.dataset_details[val].copy(), 'channels', 'ElectrodeTable')
        return electrodes_table_metadata_dict

    @property
    def ecephys_metadata(self):
        ecephys_objects = ['spikes']
        ecephys_metadata_dict = self._initialize_container_dict('EventDetection')
        current_ecephys_objects = self._get_current_object_names(ecephys_objects)
        for val, Ceid in enumerate(self.eid_list):
            ecephys_metadata_dict[val]['EventDetection'] = \
                self._get_timeseries_object(self.dataset_details[val].copy(), 'spikes', 'SpikeEventSeries')
        return ecephys_metadata_dict

    @property
    def ophys_metadata(self):
        raise NotImplementedError

    @property
    def icephys_metadata(self):
        raise NotImplementedError

    @property
    def scratch_metadata(self):
        # this can be used to add further details about subject, lab,
        raise NotImplementedError

    @property
    def complete_metadata(self):
        metafile_dict = [dict()]*len(self.eid_list)
        for val, Ceid in enumerate(self.eid_list):
            metafile_dict[val] = {**self.eid_metadata[val],
                                  **self.nwbfile_metadata[val],
                                  **self.subject_metadata[val],
                                  **self.behavior_metadata[val],
                                  **self.trials_metadata[val],
                                  **self.stimulus_metadata[val],
                                  **self.units_metadata[val],
                                  **self.electrodetable_metadata[val],
                                  'Ecephys': {**self.ecephys_metadata[val],
                                              **self.device_metadata[val],
                                              **self.electrodegroup_metadata[val],
                                              },
                                  'Ophys': dict(),
                                  'Icephys': dict()}
        return metafile_dict

    def write_metadata(self, fileloc):
        full_metadata = self.complete_metadata
        for val, Ceid in enumerate(self.eid_list):
            fileloc_upd = fileloc[:-5] + f'_eid_{val}' + fileloc[-5:]
            with open(fileloc_upd, 'w') as f:
                json.dump(full_metadata[val], f, indent=2)
