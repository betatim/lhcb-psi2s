from Ganga.GPI import *
import sys
import inspect
import os


local_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


j = Job(application=DaVinci(version="v36r4p1",
                            #version="v36r2",
                            optsfile=local_dir + "/davinci-job.py",
                            extraopts="""\nexecute()\n""",
                            #user_release_area=local_dir +"/../cmtuser/",
                            )
        )

j.outputfiles = [DiracFile("*.dst"),
                 DiracFile("*.xdst")]
j.backend = Dirac()

j.splitter = SplitByFiles(filesPerJob=10)

bk_path = "/MC/Dev/Beam6500GeV-RunII-MagUp-Nu1.6-Pythia6/Sim08f/Trig0x40b10033/Reco15DEV/28142001/DST"
bk_query = BKQuery(bk_path)

j.name = "DV psi2s"
j.comment = "DV psi2s with input from %s"%(bk_path)

j.inputdata = bk_query.getDataset()

j.prepare()
queues.add(j.submit)
