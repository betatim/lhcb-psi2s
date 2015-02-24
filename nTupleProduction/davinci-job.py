# SetupProject DaVinci v36r2
import sys

from GaudiConf import IOHelper
from Configurables import LHCbApp, ApplicationMgr, DataOnDemandSvc
from Configurables import SimConf, DigiConf, DecodeRawEvent
from Configurables import ConfigTarFileAccessSvc
from Configurables import CondDB, DaVinci
from Configurables import LoKiSvc
from Configurables import TupleToolTrigger
from Configurables import TupleToolTISTOS
from Configurables import TupleToolMCBackgroundInfo
from Configurables import CombineParticles, FilterDesktop
from Configurables import TrackAssociator, ChargedPP2MC
from Configurables import PatLHCbID2MCParticle
from TeslaTools import TeslaTruthUtils
        
from PhysSelPython.Wrappers import Selection, AutomaticData, SelectionSequence
from DecayTreeTuple.Configuration import *


def mark(idx, decay_descriptor):
    parts = decay_descriptor.split()
    parts[idx] = "^(%s)"%(parts[idx])
    return " ".join(parts)

def execute(simulation=True,
            decay_descriptor="psi(2S) -> mu- mu+"):
    # Configure all the unpacking, algorithms, tags and input files
    appConf = ApplicationMgr()
    appConf.ExtSvc+= ['ToolSvc', 'DataOnDemandSvc', LoKiSvc()]

    dv = DaVinci()
    dv.DataType = "2015"

    lhcbApp = LHCbApp()
    lhcbApp.Simulation = simulation
    CondDB().Upgrade = False
    
    dtt = DecayTreeTuple("Early2015")
    LHCbApp().DDDBtag = "dddb-20140729"
    polarity = "u"
    LHCbApp().CondDBtag = "sim-20140730-vc-m%s100"%polarity
    # either with or without muon ID applied
    muons = AutomaticData(Location="Phys/StdAllNoPIDsMuons/Particles")
    #muons = AutomaticData(Location="Phys/StdAllLooseMuons/Particles")

    psi2s = CombineParticles('MyPsi2s')
    psi2s.DecayDescriptors = [decay_descriptor]
    psi2s.CombinationCut = "(AM < 7100.0 *GeV)"
    psi2s.DaughtersCuts = {"": "ALL", "mu+": "ALL", "mu-": "ALL"}
    psi2s.MotherCut = "(VFASPF(VCHI2/VDOF) < 999999.0)"
    
    # similar to the HLT2 line
    code = """
(ADMASS('psi(2S)')< 120*MeV) &
DECTREE('%s') &
(PT>0*MeV) &
(MAXTREE('mu-'==ABSID,TRCHI2DOF) < 4) &
(MINTREE('mu-'==ABSID,PT)> 0*MeV) &
(VFASPF(VCHI2PDOF)< 25)
"""%(decay_descriptor)
    filter_psi2s = FilterDesktop("MyFilterPsi2s",
                                 Code=code,
                                 Preambulo=["vrho2 = VX**2 + VY**2"],
                                 #ReFitPVs=True,
                                 # 781 with this uncommented
                                 #IgnoreP2PVFromInputLocations=True,
                                 #WriteP2PVRelations=True
                                 )
        
    psi2s_sel = Selection("SelMyPsi2s", Algorithm=psi2s, RequiredSelections=[muons])
    filter_psi2s_sel = Selection("SelFilterMyPsi2s",
                                 Algorithm=filter_psi2s,
                                 RequiredSelections=[psi2s_sel])
    psi2s_seq = SelectionSequence("SeqMyPsi2s", TopSelection=filter_psi2s_sel)
    dtt.Inputs = [psi2s_seq.outputLocation()]
    
    # Overwriting default list of TupleTools
    dtt.ToolList = ["TupleToolKinematic",
                    "TupleToolPid",
                    "TupleToolEventInfo",
                    "TupleToolMCBackgroundInfo",
                    "TupleToolMCTruth",
                    "TupleToolGeometry",
                    #"TupleToolTISTOS",
                    # with turbo this crashes
                    "TupleToolTrackInfo",
                    "TupleToolTrigger",
                    #"TupleToolPropertime",
                    ]
    tlist = ["L0HadronDecision", "L0MuonDecision",
             "L0DiMuonDecision", "L0ElectronDecision",
             "L0PhotonDecision",
             "Hlt1DiMuonHighMassDecision", "Hlt1DiMuonLowMassDecision",
             "Hlt1TrackMuonDecision", "Hlt1TrackAllL0Decision",
             "Hlt2DiMuonJPsiDecision", "Hlt2SingleMuonDecision",
             ]
    
    dtt.addTool(TupleToolTrigger, name="TupleToolTrigger")
    dtt.addTool(TupleToolTISTOS, name="TupleToolTISTOS")
    # Get trigger info
    dtt.TupleToolTrigger.Verbose = True
    dtt.TupleToolTrigger.TriggerList = tlist
    dtt.TupleToolTISTOS.Verbose = True
    dtt.TupleToolTISTOS.TriggerList = tlist

    from Configurables import TupleToolMCTruth, MCTupleToolHierarchy

    dtt.addTool(TupleToolMCBackgroundInfo,
                name="TupleToolMCBackgroundInfo")
    dtt.TupleToolMCBackgroundInfo.Verbose = True

    mc_truth = TupleToolMCTruth()
    mc_truth.ToolList = ["MCTupleToolKinematic", "MCTupleToolHierarchy"]
    dtt.addTool(mc_truth)
    dtt.TupleToolMCTruth.Verbose = True


    relations = "Relations/Rec/ProtoP/Charged"
    TeslaTruthUtils.makeTruth(dtt,
                              relations,
                              ["MCTupleToolKinematic",
                               "MCTupleToolHierarchy",
                               "MCTupleToolPID",
                               ]
                              )
    
    dtt.Decay = mark(2, mark(3, decay_descriptor)) #"psi(2S) -> ^mu- ^mu+"
    
    dtt.addBranches({"X": "^(%s)"%(decay_descriptor),
                     "muplus": mark(3, decay_descriptor),#"psi(2S) -> mu- ^mu+",
                     "muminus": mark(2, decay_descriptor),#"psi(2S) -> ^mu- mu+",
                     })
    
    x_preamble = ["DZ = VFASPF(VZ) - BPV(VZ)",
                  ]
    x_vars = {"ETA": "ETA",
              "Y": "Y",
              "PHI": "PHI",
              "VPCHI2": "VFASPF(VPCHI2)",
              "DELTAZ": "DZ",
              # DZ * M / PZ / c with c in units of mm/s
              "TZ": "DZ*3686 / PZ/299792458000.0*(10**12)", #ps
              "minpt": "MINTREE('mu+' == ABSID, PT)",
              "minclonedist": "MINTREE(ISBASIC & HASTRACK, CLONEDIST)",
              "maxtrchi2dof": "MAXTREE(ISBASIC & HASTRACK, TRCHI2DOF)",
              }
    muon_vars = {"ETA": "ETA",
                 "Y": "Y",
                 "PHI": "PHI",
                 "CHARGE": "Q",
                 "CLONEDIST": "CLONEDIST",
                 "TRCHI2DOF": "TRCHI2DOF",
                 }
    
    loki_X = dtt.X.addTupleTool("LoKi::Hybrid::TupleTool/LoKi_X")
    loki_X.Variables = x_vars
    loki_X.Preambulo = x_preamble
    
    loki_mup = dtt.muplus.addTupleTool("LoKi::Hybrid::TupleTool/LoKi_MuPlus")
    loki_mup.Variables = muon_vars
    dtt.muplus.addTupleTool("TupleToolGeometry")
    
    loki_mum = dtt.muminus.addTupleTool("LoKi::Hybrid::TupleTool/LoKi_MuMinus")
    loki_mum.Variables = muon_vars
    dtt.muminus.addTupleTool("TupleToolGeometry")
    
    dv.TupleFile = "DVNtuples.root"
    assocpp = ChargedPP2MC("TimsChargedPP2MC")
    #assocpp.OutputLevel = 1
    dv.UserAlgorithms = [psi2s_seq.sequence(), assocpp, dtt]

#import GaudiPython as GP
#inputFiles = ["/tmp/thead/EarlyEvents-Extended-L0-Turbo.xdst"]
#IOHelper('ROOT').inputFiles(inputFiles) 
#execute()
