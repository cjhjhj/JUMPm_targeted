#!/usr/bin/python
##################################################################################################################################
#JUMP_isotope_ditsribution calculation
#Modified program for C13 isotope tracing project lead by Haiyan tan
#Program version v1.1
##################################################################################################################################
import re, numpy as np, pandas as pd, pickle, sys
from collections import defaultdict

#################################################################
def getParams(paramFile):
    parameters = dict()
    with open(paramFile, 'r') as file:
        for line in file:
            if re.search(r'^#', line) or re.search(r'^\s', line):
                continue
            line = re.sub(r'#.*', '', line)  # Remove comments (start from '#')
            line = re.sub(r'\s*', '', line)  # Remove all whitespaces

            # Exception for "feature_files" parameter
            if "feature_files" in parameters and line.endswith("feature"):
                parameters["feature_files"].append(line)
            else:
                key = line.split('=')[0]
                val = line.split('=')[1]
                if key == "feature_files":
                    parameters[key] = [val]
                else:
                    parameters[key] = val
    return parameters

"""std_aa_comp{}
A dictionary with elemental compositions of the twenty standard
amino acid residues, amino acid modifications, selenocysteine, pyrrolysine,
and standard H- and -OH terminal groups.
"""
std_aa_comp = {
    'A':   {'H': 5, 'C': 3, 'O': 1, 'N': 1},
    'C':   {'H': 5, 'C': 3, 'O': 1, 'N': 1, 'S': 1, }, #Static modification of cysteine alkylation (addition of C2H3NO)
    'D':   {'H': 5, 'C': 4, 'O': 3, 'N': 1},
    'E':   {'H': 7, 'C': 5, 'O': 3, 'N': 1},
    'F':   {'H': 9, 'C': 9, 'O': 1, 'N': 1},
    'G':   {'H': 3, 'C': 2, 'O': 1, 'N': 1},
    'H':   {'H': 7, 'C': 6, 'O': 1, 'N': 3,},
    'I':   {'H': 11,'C': 6, 'O': 1, 'N': 1},
    'K':   {'H': 12,'C': 6, 'O': 1, 'N': 2},
    'L':   {'H': 11,'C': 6, 'O': 1, 'N': 1},
    'M':   {'H': 9, 'C': 5, 'O': 1, 'N': 1, 'S': 1, },
    'N':   {'H': 6, 'C': 4, 'O': 2, 'N': 2},
    'P':   {'H': 7, 'C': 5, 'O': 1, 'N': 1},
    'Q':   {'H': 8, 'C': 5, 'O': 2, 'N': 2},
    'R':   {'H': 12,'C': 6, 'O': 1, 'N': 4},
    'S':   {'H': 5, 'C': 3, 'O': 2, 'N': 1},
    'T':   {'H': 7, 'C': 4, 'O': 2, 'N': 1},
    'V':   {'H': 9, 'C': 5, 'O': 1, 'N': 1},
    'W':   {'H': 10,'C': 11,'O': 1, 'N': 2, },
    'Y':   {'H': 9, 'C': 9, 'O': 2, 'N': 1},
    'U':   {'H': 5, 'C': 3, 'O': 1, 'N': 1, 'Se' : 1},
    'O':   {'H': 19, 'C': 12, 'O': 2, 'N': 3},
    'H-':  {'H': 1},
    '-OH': {'O': 1, 'H': 1},
    }

elemInfo_dict = {}		

def element_isoDistr_1toM(iso_mass_inten_dict, element, M, large_num_to_store, inten_threshold_trim):
    large_num_array = []
    for n in (large_num_to_store) :
        large_num_array.append(np.repeat(n, 9).tolist())
    large_num_array = [j for i in large_num_array for j in i]
    for i in range(2,M):
        element_intensity_temp = np.matrix(iso_mass_inten_dict[element]['Intensity'][1]).T * np.matrix(iso_mass_inten_dict[element]['Intensity'][i-1])
        element_mass_temp = np.matrix(iso_mass_inten_dict[element]['Mass'][1]).T + np.matrix(iso_mass_inten_dict[element]['Mass'][i-1])
        element_intensity_temp = np.array([element_intensity_temp[::-1,:].diagonal(i).sum() for i in range(-element_intensity_temp.shape[0]+1,element_intensity_temp.shape[1])])
        element_mass_temp = np.array([np.asarray(element_mass_temp[::-1,:].diagonal(i))[0][0] for i in range(-element_mass_temp.shape[0]+1,element_mass_temp.shape[1])])
        element_mass_temp_1 = np.array(element_mass_temp); element_mass_temp_1 = element_mass_temp_1[np.array(element_intensity_temp)>1e-5]
        element_intensity_temp_1 = np.array(element_intensity_temp); element_intensity_temp_1 = element_intensity_temp_1[np.array(element_intensity_temp)>1e-5]
        iso_mass_inten_dict[element]['Intensity'][i] = element_intensity_temp[element_intensity_temp > inten_threshold_trim]#element_intensity_temp_1
        iso_mass_inten_dict[element]['Mass'][i] = element_mass_temp[element_intensity_temp > inten_threshold_trim]#element_mass_temp_1
    # generating lement istopic peaks for 1000, 10000, 100000... so on upto 10E8
    if len(large_num_array) > 0:
        iso_inten_temp= iso_mass_inten_dict[element]['Intensity'][large_num_array[0]]
        iso_mass_temp= iso_mass_inten_dict[element]['Mass'][large_num_array[0]]
        current_num = large_num_array[0]
        inten_threshold_trim2 = 1e-10
        for n in large_num_array:
            current_num += n
            element_intensity_temp = np.matrix(iso_mass_inten_dict[element]['Intensity'][n]).T * np.matrix(iso_inten_temp)
            element_mass_temp = np.matrix(iso_mass_inten_dict[element]['Mass'][n]).T + np.matrix(iso_mass_temp)
            iso_inten_temp = np.array([element_intensity_temp[::-1,:].diagonal(i).sum() for i in range(-element_intensity_temp.shape[0]+1,element_intensity_temp.shape[1])])
            iso_mass_temp  = np.array([np.asarray(element_mass_temp[::-1,:].diagonal(i))[0][0] for i in range(-element_mass_temp.shape[0]+1,element_mass_temp.shape[1])])
            iso_mass_temp = iso_mass_temp[iso_inten_temp > inten_threshold_trim2]
            iso_inten_temp = iso_inten_temp[iso_inten_temp > inten_threshold_trim2]
            if current_num in large_num_to_store:
                iso_mass_inten_dict[element]['Intensity'][current_num] =iso_inten_temp[iso_inten_temp > inten_threshold_trim]
                iso_mass_inten_dict[element]['Mass'][current_num] = iso_mass_temp[iso_inten_temp > inten_threshold_trim]
    return iso_mass_inten_dict

### creating a dictionary with isotopic peak intensity and mass for the mono elemnts ( with cutoff )  
def isotope_distribution_indElement(elemInfo_dict, iso_mass_inten_dict, inten_threshold_trim ):
    inten_threshold_trim = 1e-10
    for element in list(elemInfo_dict.keys()):
        print('Genrating dictionary for ',element)
        iso_mass_inten_dict[element]= {'Mass':{1:list(elemInfo_dict[element].keys())}, 'Intensity':{1:list(elemInfo_dict[element].values())}}
        iso_mass_inten_dict = element_isoDistr_1toM(iso_mass_inten_dict, element, 51, [], inten_threshold_trim)
    return iso_mass_inten_dict

					
# module to convert the aminoacid seq to chemical element dictionary    
def pepSeq_to_chemComp(pep_seq, Charge, aa_comp,TMT_Plex ):
    chem_comp = defaultdict(int)
    for aa in pep_seq:
        if aa in aa_comp:
            for elem, cnt in aa_comp[aa].items():
                chem_comp[elem] += cnt
        else:
            print('No information for %s in `aa_comp`' % aa)
    chem_comp['H'] += 2 +(1*Charge)
    chem_comp['O'] += 1
    
    #Add TMT balancer
    count_K = pep_seq.count('K')
    if TMT_Plex == 'TMTPro': 
        chem_comp['C'] += 8*(count_K+1)
        chem_comp['N'] += 1*(count_K+1)
        chem_comp['H'] += 25*(count_K+1)
        chem_comp['O'] += 3*(count_K+1)
        
        chem_comp['x'] += 7*(count_K+1) # x = C13
        chem_comp['y'] += 2*(count_K+1) # y = N15
 
    if TMT_Plex == 'TMT10':
        chem_comp['C'] += 8*(count_K+1)
        chem_comp['N'] += 1*(count_K+1)
        chem_comp['H'] += 20*(count_K+1)
        chem_comp['O'] += 2*(count_K+1)
        
        chem_comp['x'] += 4*(count_K+1) # x = C13
        chem_comp['y'] += 1*(count_K+1) # y = N15
    return chem_comp

def gen_array_combi(n, element):
    com_array = []
    c=0
    if element in ['C', 'N', 'H','O']:
        while(n > 0): 
            r=n%10 
            if ((c > 1) & (r>1)):
                com_array.append(np.repeat(int((r*(10**c))/r), r).tolist())
            elif (r>0):    
                com_array.append([r*(10**c)])
            c+=1 
            n//=10
    elif element == 'S':
        while(n > 0): 
            r=n%10 
            if ((c >= 1) & (r>1)):
                com_array.append(np.repeat(int((r*(10**c))/r), r).tolist())
            elif (r>0):    
                com_array.append([r*(10**c)])
            c+=1 
            n//=10
    else:
        while(n > 0): 
            r=n%10 
            if ((c >= 0) & (r>0)):
                com_array.append(np.repeat(int((r*(10**c))/r), r).tolist())
            elif (r>0):    
                com_array.append([r*(10**c)])
            c+=1 
            n//=10
    com_array = [j for i in com_array for j in i]
    return com_array    

def iso_distri_largeNum(element, count, iso_mass_inten_dict):
    print('iso_distri_largeNum --  element = ', element, 'count = ', count)
    gen_iso_combi_array = gen_array_combi(count, element)
    iso_inten_temp= iso_mass_inten_dict[element]['Intensity'][gen_iso_combi_array[0]]
    iso_mass_temp= iso_mass_inten_dict[element]['Mass'][gen_iso_combi_array[0]]
    for n in gen_iso_combi_array[1:]:
        element_intensity_temp = np.matrix(iso_mass_inten_dict[element]['Intensity'][n]).T * np.matrix(iso_inten_temp)
        element_mass_temp = np.matrix(iso_mass_inten_dict[element]['Mass'][n]).T + np.matrix(iso_mass_temp)
        iso_inten_temp = np.array([element_intensity_temp[::-1,:].diagonal(i).sum() for i in range(-element_intensity_temp.shape[0]+1,element_intensity_temp.shape[1])])
        iso_mass_temp  = np.array([np.asarray(element_mass_temp[::-1,:].diagonal(i))[0][0] for i in range(-element_mass_temp.shape[0]+1,element_mass_temp.shape[1])])
    pep_iso_distr_df = pd.DataFrame(iso_inten_temp, columns = ['isotope_inten'])
    pep_iso_distr_df['isotope_mass'] =  iso_mass_temp
    return pep_iso_distr_df
pd.set_option('mode.chained_assignment', None)


def iso_distri_combine_eleme(pep_iso_distr_df,next_elem_iso_inesity_distr,next_elem_iso_mass_distr, mass_tolerance,select_weighted_mass, select_strong_intensity_peaks):
    peptide_intensity = np.matrix(pep_iso_distr_df.isotope_inten.values).T * np.matrix(next_elem_iso_inesity_distr)
    peptide_mass = (np.matrix(pep_iso_distr_df.isotope_mass.values).T + np.matrix(next_elem_iso_mass_distr))
    pep_iso_distr_df = pd.DataFrame((np.concatenate((peptide_mass.flatten().T, peptide_intensity.flatten().T),axis = 1)), columns=["isotope_mass", "isotope_inten"])
    pep_iso_distr_df = pep_iso_distr_df[pep_iso_distr_df.isotope_inten > 1e-10].sort_values(['isotope_inten'],ascending=[False])
    if pep_iso_distr_df.shape[0] > 50000:
        pep_iso_distr_df = pep_iso_distr_df.head(50000)
    return pep_iso_distr_df


def iso_distri_(iso_mass_inten_dict, chemical_com, Charge, isotope_cutoff, mass_tolerance, select_weighted_mass, select_strong_intensity_peaks ):
    default_elementDict_size = {'C': 200,'N': 100, 'H': 300,'O':100,'S': 10, 'P': 2, 'F': 2, 'Na': 2, 'K': 2, 'Si': 2, 'Cl': 2, 'Mg': 2, 'Fe': 2, 'Ca': 2, 'Zn': 2, 'Br': 2, 'Pb': 2, 'Cu': 2, 'Al': 2, 'Cd': 2, 'I': 2, 'Ti': 2, 'B': 2, 'Se': 2, 'Ni': 2, 'Mn': 2, 'As': 2, 'Li': 2, 'Mo': 2, 'Co': 2}
    if any(chemical_com[k] > default_elementDict_size[k] for k in set(chemical_com).intersection(default_elementDict_size)): #if any(k > 200 for k in list(chemical_com.values())):
        for element, count in list(chemical_com.items())[:1]:
            if count > default_elementDict_size[element]:
                pep_iso_distr_df = iso_distri_largeNum(element, count,iso_mass_inten_dict)
            else: #if elemnt count is not grater than deafaults size       
                pep_iso_distr_df = pd.DataFrame((iso_mass_inten_dict_trimed[element]['Intensity'][count]), columns = ['isotope_inten'])
                pep_iso_distr_df['isotope_mass'] =  (iso_mass_inten_dict_trimed[element]['Mass'][count])
            
        for element, count in list(chemical_com.items())[1:]:
            if count > default_elementDict_size[element]:
                pep_iso_distr_df_ = iso_distri_largeNum(element, count,iso_mass_inten_dict)
                pep_iso_distr_df = iso_distri_combine_eleme(pep_iso_distr_df,pep_iso_distr_df_.isotope_inten.values, pep_iso_distr_df_.isotope_mass.values, mass_tolerance, select_weighted_mass, select_strong_intensity_peaks)
            else:
                pep_iso_distr_df = iso_distri_combine_eleme(pep_iso_distr_df,iso_mass_inten_dict_trimed[element]['Intensity'][count], iso_mass_inten_dict_trimed[element]['Mass'][count], mass_tolerance,select_weighted_mass, select_strong_intensity_peaks)
    else: # if any elemnt size is not greater than default elemnts size 
        for element, count in list(chemical_com.items())[:1]:
            pep_iso_distr_df = pd.DataFrame((iso_mass_inten_dict_trimed[element]['Intensity'][count]), columns = ['isotope_inten'])
            pep_iso_distr_df['isotope_mass'] =  (iso_mass_inten_dict_trimed[element]['Mass'][count])
            
        for element, count in list(chemical_com.items())[1:]: #chemical_com.items():
            pep_iso_distr_df = iso_distri_combine_eleme(pep_iso_distr_df,iso_mass_inten_dict_trimed[element]['Intensity'][count], iso_mass_inten_dict_trimed[element]['Mass'][count], mass_tolerance,select_weighted_mass, select_strong_intensity_peaks)
            
    pep_iso_distr_df.columns = ["pep_mass", "pep_intensity"]
    pep_iso_distr_df = pep_iso_distr_df.sort_values(['pep_intensity'],ascending=[False])
    pep_iso_distr_df_temp = pep_iso_distr_df[pep_iso_distr_df.pep_intensity > 1e-10].sort_values(['pep_intensity'],ascending=[False])
    pep_iso_distr_df_temp['groups'] = 0
    i = 0
    while len(pep_iso_distr_df_temp.loc[pep_iso_distr_df_temp['groups']==0,'pep_intensity']) > 0:
        i +=1
        maxIntensity_isopeak = (pep_iso_distr_df_temp.loc[pep_iso_distr_df_temp.groups == 0])['pep_mass'].values[0]
        lb = (maxIntensity_isopeak - mass_tolerance*maxIntensity_isopeak/1e6)#[0]
        ub = (maxIntensity_isopeak + mass_tolerance*maxIntensity_isopeak/1e6)#[0]
        pep_iso_distr_df_temp.loc[pep_iso_distr_df_temp['pep_mass'].between(lb, ub, inclusive=False), 'groups'] =i
    pep_iso_distr_df = pep_iso_distr_df_temp.copy()
    if select_weighted_mass ==1:
        pep_iso_distr_df['Rel_inten']     = pep_iso_distr_df['pep_intensity']/pep_iso_distr_df.groupby('groups')['pep_intensity'].transform('sum')
        pep_iso_distr_df['weighted_mass'] = pep_iso_distr_df['pep_mass']*pep_iso_distr_df['Rel_inten']
        pep_iso_distr_df = pep_iso_distr_df.groupby(['groups']).agg(isotope_mass=('weighted_mass', 'sum'),isotope_inten=('pep_intensity', 'sum'))
    elif select_strong_intensity_peaks == 1:
        pep_iso_distr_df = pep_iso_distr_df.groupby(['groups']).agg(isotope_mass=('pep_mass', 'first'),isotope_inten=('pep_intensity', 'sum'))
    
    return pep_iso_distr_df
             
def iso_distri(iso_mass_inten_dict_trimed, chemical_com, Charge, isotope_cutoff, mass_tolerance, select_strong_intensity_peaks, is_pep):
    if select_strong_intensity_peaks == 1:
        pep_iso_distr_df = iso_distri_(iso_mass_inten_dict_trimed, chemical_com, Charge, isotope_cutoff, mass_tolerance, select_weighted_mass = 0, select_strong_intensity_peaks = 1 )
    else: # if user wants to merge isotopic peaks within mass_tolerance using weighted average of intensity   
        pep_iso_distr_df = iso_distri_(iso_mass_inten_dict_trimed, chemical_com, Charge, isotope_cutoff, mass_tolerance, select_weighted_mass=1, select_strong_intensity_peaks=0 )
    #print(pep_iso_distr_df)
    pep_iso_distr_df['isotope_mass'] = (pep_iso_distr_df['isotope_mass'].values + 1.007276466812000* Charge)/abs(Charge)  # electron mass

    #print(pep_iso_distr_df)
    pep_iso_distr_df['isotope_inten']= pep_iso_distr_df.isotope_inten/pep_iso_distr_df.isotope_inten.max()
    pep_iso_distr_df = pep_iso_distr_df[pep_iso_distr_df['isotope_inten'] > isotope_cutoff]
    pep_iso_distr_df['isotope_inten']= (pep_iso_distr_df.isotope_inten/pep_iso_distr_df.isotope_inten.sum())*100

    return pep_iso_distr_df

#############################################################################  Main program strats here #######################################
#paramFile= "Z:/ResearchHome/ClusterHome/schepyal/isotope_tracing/jump_iso_distri.params"
paramFile = sys.argv[1]
print("paramFile = ", paramFile)
params = getParams(paramFile)

if 'PTM_Phosphorilation' in params:
    if any(params['PTM_Phosphorilation']):
        std_aa_comp.update({params['PTM_phosphorylation']: {'H': 1,'P': 1,'O': 3}})
    else:
        std_aa_comp.update({'#': {'H': 1,'P': 1,'O': 3}})

if 'PTM_mono_oxidation' in params:
    std_aa_comp.update({params['PTM_mono_oxidation']: {'O': 1}})

####################################################    Step-1    ##################################################################
#####################################################################################################################################
##### Open the default elemntary dictonary
with open(params['element_dict_trimmed'], 'rb') as f:
    iso_mass_inten_dict_trimed = pickle.load(f)    

####################################################    Step-2    ##################################################################
#####################################################################################################################################
### Update the elemntary dictonary with user defined tracer elements and their natural abundance
if ('Tracer_elem_1' in params): 
    if (params['Tracer_elem_1'] == '13C'):
        elemInfo_dict.update({"x": {12: 1-float(params['Tracer_elem_1_purity']), 13.00335483521: float(params['Tracer_elem_1_purity'])}})
    elif(params['Tracer_elem_1'] == '15N'):
        elemInfo_dict.update({"y": {14.00307400446: 1-float(params['Tracer_elem_1_purity']), 15.0001088989: float(params['Tracer_elem_1_purity'])}}) 
    else:
        print("\n Information for parameter \"Tracer_elem_1\" is not properly defined\n ")
        
if ('Tracer_elem_2' in params): 
    if (params['Tracer_elem_2'] == '13C'):
        elemInfo_dict.update({"x": {12: 1-float(params['Tracer_elem_2_purity']), 13.00335483521: float(params['Tracer_elem_2_purity'])}})
    elif(params['Tracer_elem_2'] == '15N'):
        elemInfo_dict.update({"y": {14.00307400446: 1-float(params['Tracer_elem_2_purity']), 15.0001088989: float(params['Tracer_elem_2_purity'])}}) 
    else:
        print("\n Information for parameter \"Tracer_elem_2\" is not properly defined\n ")    
    
iso_mass_inten_dict_trimed = isotope_distribution_indElement(elemInfo_dict,  iso_mass_inten_dict_trimed, inten_threshold_trim = 1e-10)

print("\nElement isotope dictionary is updated with tracer elemnts (eg. C13)\n")
 

####################################################    Step-3   ##################################################################
########################## Reading a input file and calculate the isotopic distribution for metabolites   #########################
  
print("\nReading the input file and calculating the isotopic distribution for the metabolites  topologues\n")

input_file = (pd.read_excel(params['input_file'],sheet_name= 'User-Input', index_col = 0,skiprows=[0]))
iso_distr_all = pd.DataFrame(columns=['iso_topologus', 'isotope_M/Z', 'isotope_intensity']) 
inputData = pd.DataFrame()
for i in range(1,len(input_file)):
    chemical_com = {k: int(v) if v else 1 for k,v in re.findall(r"([A-Z][a-z]?)(\d+)?", input_file.formula[i])}
    chemical_com_ = chemical_com.copy()
    for j in range(0, chemical_com["C"]+1):
        chemical_com_ = chemical_com.copy()
        if input_file.tracer[i] == 'C13':
            chemical_com_["C"] = chemical_com_["C"]-j
            chemical_com_["x"] = j #x = C13
            chemical_com_ = {k:v for k,v in chemical_com_.items() if v != 0}
        elif input_file.tracer[i] == 'N15':
            chemical_com_["N"] = chemical_com_["N"]-j
            chemical_com_["y"] = j #x = N15
            chemical_com_ = {k:v for k,v in chemical_com_.items() if v != 0}    
        #print(chemical_com_)
        iso_distr = iso_distri(iso_mass_inten_dict_trimed, chemical_com_, input_file.z[i], float(params['isotope_cutoff']), float(params['mass_tolerance']), float(params['strong_isotopic_peaks']), is_pep =0)
        if 'groups' in iso_distr.columns:
            iso_distr.drop(['groups'],axis=1,inplace=True)
        iso_distr_all = iso_distr_all.append({'iso_topologus': 'M'+str(j),'isotope_M/Z': ';'.join([str(f) for f in iso_distr.isotope_mass.values]), 'isotope_intensity': ';'.join([str(f) for f in iso_distr.isotope_inten.values])}, ignore_index=True)
        inputData = inputData.append(input_file.iloc[i,:], ignore_index=True)
    
iso_distr_all = pd.concat([inputData, iso_distr_all], axis=1)        

####################################################       Step-4       ##################################################################
####################################################  OUTPUT printing   ##################################################################

writer  = pd.ExcelWriter(params['output_file']+".xlsx", engine='xlsxwriter'); # Create a Pandas Excel writer using XlsxWriter as the engine.
iso_distr_all.to_excel(writer, sheet_name='isotope_distri',index=False)
writer.save(); writer.close()

print("\nCompleted writing isotopic distribution to out-file\n")
print("\nThe Program completed succesfully\n")
