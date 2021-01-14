import numpy as np
import scipy
from scipy import special
#from zfel import general_load_bucket
from . import general_load_bucket
import matplotlib.pyplot as plt 

# Some constant values
alfvenCurrent = 17045.0 # Alfven current ~ 17 kA
mc2 = 0.51099906E6#510.99906E-3      # Electron rest mass in eV
c = 2.99792458E8        # light speed in meter
e = 1.60217733E-19      # electron charge in Coulomb
epsilon_0=8.85418782E-12 #electric constant
hbar=6.582e-16          #in eV


def sase(inp_struct):
    '''
    SASE 1D FEL run function
    Input:
    npart                       # n-macro-particles per bucket 
    s_steps                     # n-sample points along bunch length
    z_steps                     # n-sample points along undulator
    energy                      # electron energy [MeV]
    eSpread                     # relative rms energy spread [ ]
    emitN                       # normalized transverse emittance [mm-mrad]
    currentMax                  # peak current [Ampere]
    beta                        # mean beta [meter]
    unduPeriod                  # undulator period [meter]
    unduK                       # undulator parameter, K [ ]
    unduL                       # length of undulator [meter]
    radWavelength               # seed wavelength? [meter], used only in single-freuqency runs
    dEdz                        # rate of relative energy gain or taper [keV/m], optimal~130
    iopt                        # 'sase' or 'seeded'
    P0                          # small seed input power [W]
    constseed                   # whether we want to use constant  random seed for reproducibility, 1 Yes, 0 No
    particle_position           # particle information with positions in meter and eta
    hist_rule                   # different rules to select number of intervals to generate the histogram of eta value in a bucket

    Output:
    z                           # longitudinal steps along undulator
    power_z                     # power profile along undulator                    
    s                           # longitudinal steps along beam
    power_s                     # power profile along beam    
    rho                         # FEL Pierce parameter
    detune                      # deviation from the central energy
    field                       # final output field along beam
    field_s                     # output field along beam for different z position
    gainLength                  # 1D FEL gain Length
    resWavelength               # resonant wavelength
    thet_out                    # output phase
    eta_out                     # output energy in unit of mc2
    bunching                    # bunching factor
    spectrum                    # spectrum power
    freq                        # frequency in ev
    Ns                          # real number of examples
    '''
    #calculating intermediate parameters
    params=params_calc(**inp_struct)
    
    #loaduckets
    bucket_params={'npart':inp_struct['npart']
        ,'Ns':params['Ns'],'coopLength':params['coopLength'],\
        'particle_position':inp_struct['particle_position'],'s_steps':inp_struct['s_steps'],\
        'dels':params['dels'],'hist_rule':inp_struct['hist_rule'],'gbar':params['gbar'],\
        'delg':params['delg'],'iopt':inp_struct['iopt']}
    bucket_data=general_load_bucket.general_load_bucket(**bucket_params)
    
    #FEL process
    FEL_params={}
    FEL_params.update(inp_struct)
    FEL_params.update(params)
    FEL_params.update(bucket_data)
    FEL_data=FEL_process(**FEL_params)

    #finalize calculation
    final_params={}
    final_params.update(FEL_data)
    final_params.update(FEL_params)
    final_data=final_calc(**final_params)

    #unpack outputs
    gainLength    = params['gainLength']
    resWavelength = params['resWavelength']
    thet_out      = final_data['thet_out']
    eta_out       = final_data['eta_out']
    bunching      = FEL_data['bunching']
    
    Ns       = params['Ns']
    history  = final_data['history']
    spectrum = history['spectrum']
    freq     = history['freq']
    z        = history['z']
    power_z  = history['power_z']
    s        = history['s']
    power_s  = history['power_s']
    rho      = history['rho']
    detune   = history['detune']
    field    = history['field']
    field_s  = history['field_s']
    return z,power_z,s,power_s,rho,detune,field,field_s,gainLength,resWavelength,thet_out,eta_out,bunching,spectrum,freq,Ns,history

def params_calc(npart,s_steps,z_steps,energy,eSpread,\
            emitN,currentMax,beta,unduPeriod,unduK,unduL,radWavelength,\
            dEdz,iopt,P0,constseed,particle_position,hist_rule):
    '''
    calculating intermediate parameters
    '''
    # whether to use constant random seed for reproducibility
    if constseed==1:
        np.random.seed(31)

    #Check if unduK is array
    if not isinstance(np.ndarray):
        unduK = unduK*np.array([1])

    unduJJ  = scipy.special.jv(0,unduK**2/(4+2*unduK**2))\
              -scipy.special.jv(1,unduK**2/(4+2*unduK**2))  # undulator JJ
    gamma0  = energy/mc2                                    # central energy of the beam in unit of mc2
    sigmaX2 = emitN*beta/gamma0                             # rms transverse size, divergence of the electron beam

    kappa_1 = e*unduK*unduJJ/4/epsilon_0/gamma0
    density = currentMax/(e*c*2*np.pi*sigmaX2)
    Kai     = e*unduK*unduJJ/(2*gamma0**2*mc2*e)
    ku      = 2*np.pi/unduPeriod


    rho     = (0.5/gamma0)*((currentMax/alfvenCurrent)\
              *(unduPeriod*unduK*unduJJ/(2*np.pi))**2\
              /(2*sigmaX2))**(1/3)                          # FEL Pierce parameter
    
    resWavelength = unduPeriod*(1+unduK[0]**2/2.0)\
                    /(2*gamma0**2)                          # resonant wavelength

    #Pbeam   = energy*currentMax*1000.0                     # rho times beam power [GW]
    Pbeam      = energy*currentMax                          # beam power [W]
    coopLength = resWavelength/unduPeriod                   # cooperation length
    gainLength = 1                                          # rough gain length
    #cs0  = bunchLength/coopLength                          # bunch length in units of cooperation length     
    z0    = unduL#/gainLength                               # wiggler length in units of gain length
    delt  = z0/z_steps                                      # integration step in z0 ~ 0.1 gain length
    dels  = delt                                            # integration step in s0 must be same as in z0 
    E02   = density*kappa_1[0]*P0/Pbeam/Kai[0]              # scaled input power
    gbar  = (resWavelength-radWavelength)\
            /(radWavelength)                                # scaled detune parameter
    delg  = eSpread                                         # Gaussian energy spread in units of rho 
    Ns    = currentMax*unduL/unduPeriod/z_steps\
            *resWavelength/c/e                              # N electrons per s-slice [ ]
    #Eloss = -dEdz*1E-3/energy/rho*gainLength               # convert dEdz to alpha parameter
    deta  = np.sqrt((1+0.5*unduK[0]**2)/(1+0.5*unduK**2))-1



    params={'unduJJ':unduJJ,'gamma0':gamma0,'sigmaX2':sigmaX2,'kappa_1':kappa_1,'density':density,\
    'Kai':Kai,'ku':ku,'resWavelength':resWavelength,'Pbeam':Pbeam,'coopLength':coopLength,'z0':z0,\
    'delt':delt,'dels':dels,'E02':E02,'gbar':gbar,'delg':delg,'Ns':Ns,'deta':deta,'rho':rho,'gainLength':gainLength}

    return params



def FEL_process(npart,z_steps,energy,eSpread,\
            emitN,currentMax,beta,unduPeriod,unduK,unduL,radWavelength,\
            dEdz,iopt,P0,constseed,particle_position,hist_rule,\
            unduJJ,gamma0,sigmaX2,kappa_1,density,\
            Kai,ku,resWavelength,Pbeam,coopLength,z0,\
            delt,dels,E02,gbar,delg,Ns,deta,\
            thet_init,eta_init,N_real,s_steps,rho,gainLength):    

    s = np.arange(1,s_steps+1)*dels*coopLength*1.0e6      # longitundinal steps along beam in micron ? meter           
    z = np.arange(1,z_steps+1)*delt*gainLength            # longitundinal steps along undulator in meter

    bunchLength = s[-1]*1e-6                              # beam length in meter
    bunch_steps = np.round(bunchLength/delt/coopLength)   # rms (Gaussian) or half width (flattop) bunch length in s_step
    shape       = N_real/np.max(N_real)

    # sase mode is chosen, go over all slices of the bunch starting from the tail k=1
    if iopt=='sase': 
        # initialization of variables during the 1D FEL process
        Er  = np.zeros((s_steps+1,z_steps+1))
        Ei  = np.zeros((s_steps+1,z_steps+1))
        eta = np.zeros((npart,z_steps+1))
        thet_output = np.zeros((npart,z_steps+1))
        thethalf    = np.zeros((npart,z_steps+1))
        thet_out    = np.zeros((s_steps,1))
        bunching    = np.zeros((s_steps,z_steps),dtype=complex)
        for k in range(s_steps):
            Er[k,0]  = np.sqrt(E02)                                              # input seed signal
            Ei[k,0]  = 0.0
            thet0    = thet_init[k,:]
            eta0     = eta_init[k,:]
            eta[:,0] = eta0.T
            thet_output[:,0] = thet0.T                                                   # eta at j=1
            thethalf[:,0]    = thet0.T-2*ku*eta[:,0]*delt/2                             # half back
            thet_out[k,0]    = np.mean(thet0.T)
            for j in range(z_steps):                                            # evolve e and eta in s and t by leap-frog
                thet   = thethalf[:,j]+2*ku*(eta[:,j]+deta[j])*delt/2
                sumsin = np.sum(np.sin(thet))
                sumcos = np.sum(np.cos(thet)
                sinavg = shape[k]*sumsin/npart
                cosavg = shape[k]*sumcos/npart
                Erhalf = Er[k,j]+kappa_1[j]*density * cosavg*dels/2   #minus sign 
                Eihalf = Ei[k,j]-kappa_1[j]*density * sinavg*dels/2               
                thethalf[:,j+1] = thethalf[:,j]+2*ku*(eta[:,j]+deta[j])*delt
                eta[:,j+1] = eta[:,j]-2*Kai[j]*Erhalf*np.cos(thethalf[:,j+1])*delt\
                             +2*Kai[j]*Eihalf*np.sin(thethalf[:,j+1])*delt#-Eloss*delt  #Eloss*delt to simulate the taper
                
                thet_output[:,j+1] = thet
                sumsin = np.sum(np.sin(thethalf[:,j+1]))
                sumcos = np.sum(np.cos(thethalf[:,j+1]))
                sinavg = shape[k]*sumsin/npart
                cosavg = shape[k]*sumcos/npart
                Er[k+1,j+1] = Er[k,j]+kappa_1[j]*density *cosavg*dels                               # apply slippage condition
                Ei[k+1,j+1] = Ei[k,j]-kappa_1[j]*density *sinavg*dels
                bunching[k,j] = np.mean(np.real(np.exp(-1j*thet)))\
                              +np.mean(np.imag(np.exp(-1j*thet)))*1j            #bunching factor calculation
    return {'Er':Er,'Ei':Ei,'thet_output':thet_output,'eta':eta,'s':s,'z':z,'bunching':bunching,'bunchLength':bunchLength}

def final_calc(npart,z_steps,energy,eSpread,\
            emitN,currentMax,beta,unduPeriod,unduK,unduL,radWavelength,\
            dEdz,iopt,P0,constseed,particle_position,hist_rule,\
            unduJJ,gamma0,sigmaX2,kappa_1,density,\
            Kai,ku,resWavelength,Pbeam,coopLength,z0,\
            delt,dels,E02,gbar,delg,Ns,deta,\
            thet_init,eta_init,N_real,s_steps,\
            Er,Ei,thet_output,eta,s,z,rho,gainLength,bunching,bunchLength):
 
    #converting a and eta to field, power and etaavg
    power_s = np.zeros((z_steps,s_steps))
    power_z = np.zeros(z_steps)
    etaavg  = np.zeros(z_steps)
    for j in range(z_steps):
        for k in range(s_steps):
            power_s[j,k] = (Er[k+1,j]**2+Ei[k+1,j]**2)*Kai[j]/(density*kappa_1[j])*Pbeam
        power_z[j] = np.sum(Er[:,j]**2+Ei[:,j]**2)*Kai[j]/(density*kappa_1[j])*Pbeam/s_steps
        etaavg[j]  = np.sum(eta[:,j+1])/npart # average electron energy at every z position
        thet_out   = 0 # don't output phase space
        eta_out    = 0
    detune   = 2*np.pi/(dels*s_steps)*np.arange(-s_steps/2,s_steps/2+1)
    field    = (Er[:,z_steps]+Ei[:,z_steps]*1j)*np.sqrt(Kai[z_steps-1]/(density*kappa_1[z_steps-1])*Pbeam)
    field_s  = (Er[:,:]+Ei[:,:]*1j)*np.sqrt(np.concatenate((np.array([Kai[0]]),Kai))[np.newaxis,:]/(density*np.concatenate((np.array([kappa_1[0]]),kappa_1))[np.newaxis,:]*Pbeam))
    pfft     = np.fft.fft(field_s[:,1:],axis=1)
    spectrum = np.fft.fftshift(np.absolute(pfft)**2)
    omega    = hbar * 2.0 * np.pi / (resWavelength/c)
    df       = hbar * 2.0 * np.pi*1/(bunchLength/c)
    freq     = np.linspace(omega - s_steps/2 * df, omega + s_steps/2 * df,s_steps)
    history  = {'z':z,'power_z':power_z,'s':s,'power_s':power_s,'field':field,'field_s':field_s,'thet_output':thet_output,'eta':eta,'rho':rho,'detune':detune,'iopt':iopt,'spectrum':spectrum,'freq':freq}        

    return {'history':history,'thet_out':thet_out,'eta_out':eta_out}



def plot_log_power_z(history):
    z       = history['z']
    power_z = history['power_z']
    plt.figure()
    plt.plot(z,np.log10(power_z))
    plt.xlabel('z (m)')
    plt.ylabel('log(P) (W)')

def plot_power_s(history):
    s = history['s']
    power_s = history['power_s']
    plt.figure()
    for i in range(power_s.shape[0]):
        plt.plot(s,power_s[i,:])
    plt.xlabel('s (um)')
    plt.ylabel('power at different z positions (W)')

def plot_phase_space(history):
    z = history['z']
    thet_output = history['thet_output']
    eta  = history['eta']
    iopt = history['iopt']
    rho  = history['rho']
    for j in range(z.shape[0]):
        plt.figure()
        plt.plot(thet_output[:,j],eta[:,j],'.')
        plt.xlabel('theta')
        plt.ylabel('eta')
        if iopt=='seeded':
            plt.axis([-np.pi,np.pi,-5,5])
        else:
            pass
            #plt.axis([0,9,8400000,8500000])
            #plt.axis([0,9,-2.5,2.5])
        plt.title('undulator distance (m) = '+str(z[j]))
        #pause(.02)

def plot_pspec(history):
    #need to modify
    field  = history['field']
    rho    = history['rho']
    detune = history['detune']
    plt.figure()
    fieldFFT = np.fftshift(np.fft(field.T))                  # unconjugate complex transpose by .'
    Pspec=fieldFFT*np.conj(fieldFFT)
    plt.plot(detune*2*rho,Pspec)
    plt.axis([-0.06,+0.01,0,1.2*np.max(Pspec)])
    plt.xlabel('{(\Delta\omega)/\omega_r}')
    plt.ylabel('{output spectral power} (a.u.)')


def plot_norm_power_s(history):
    #need to modify
    power_s = history['power_s']
    z = history['z']
    s = history['s']
    z_steps = z.shape[0]
    s_steps = s.shape[0]
    Y,X = np.meshgrid(z[1:],s);
    p_norm = power_s[1:,:]
    for k in np.arange(0,z_steps-1):
        p_norm[k,:] = p_norm[k,:]/np.max(p_norm[k,:])


def plot_current(history):
    shape = history['shape']
    plt.figure()
    plt.plot(shape)
    plt.title('Current')




