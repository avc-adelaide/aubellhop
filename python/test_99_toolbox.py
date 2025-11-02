"""
    Test all 2D Bellhop examples from the acoustics toolbox and verify
    that bellhop.py can read the .env files and produce the same results as
    running bellhop.exe directly.

    This is too slow to include in the standard test suite.
    Run it manually with:

    pytest --capture=tee-sys --verbose python/test_99_toolbox.py
"""
import time
import csv
import os
import pytest
import pandas.testing as pdt
import bellhop as bh

# CSV file for timing and pass/fail results
RESULTS_FILE = "python/test_results.csv"

# Initialise CSV only once at session start
@pytest.fixture(scope="session", autouse=True)
def init_csv():
    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["envfile", "time_sec", "status"])
    yield


# The big parameterized test
@pytest.mark.parametrize("envfile", [
    # TODO: check missing entries against this list automatically
    "examples/calib/calibK.env",
    "examples/calib/calibSgrad.env",
    "examples/calib/calibB_Cerveny.env",
    "examples/calib/calibB_gb.env",
    "examples/calib/calibBgrad.env",
    "examples/calib/calibKgrad.env",
    "examples/calib/calibB.env",
    "examples/calib/calibBgrad_gb.env",
    "examples/calib/calibray.env",
    "examples/calib/calibS.env",
    "examples/calib/calibBarr.env",
    "examples/calib/calibraygrad.env",
    "examples/VolAtt/free_FGB.env",
    "examples/VolAtt/free_gbtB.env",
    "examples/VolAtt/free_FGS.env",
    "examples/VolAtt/free_ThorpB.env",
    "examples/VolAtt/free_ThorpS.env",
    "examples/VolAtt/freeS.env",
    "examples/VolAtt/free_gbtB_Inc.env",
    "examples/VolAtt/freeB.env",
    "examples/VolAtt/freeB_Inc.env",
    "examples/iso.env",
    "examples/MunkLeaky/MunkKleaky.env",
    "examples/MunkLeaky/MunkK1501.env",
    "examples/MunkLeaky/MunkS.env",
    "examples/MunkLeaky/MunkK1510.env",
    "examples/MunkLeaky/MunkKbb.env",
    "examples/MunkLeaky/MunkKwb.env",
    "examples/MunkLeaky/MunkK1525.env",
    "examples/arctic/arctic.env",
    "examples/arctic/arcticB_cpp.env",
    "examples/arctic/arcticK.env",
    "examples/arctic/arctic2layB.env",
    "examples/arctic/arcticB.env",
    "examples/arctic/arcticS.env",
    "examples/arctic/arcticB_gb.env",
    "examples/free/freePoint_ParaxialB.env",
    "examples/free/freeLineB.env",
    "examples/free/freeLine_ParaxialB.env",
    "examples/free/freePointB.env",
    "examples/free/freeSPoint.env",
    "examples/free/freeLine_gbtB.env",
    "examples/free/freeSLine.env",
    "examples/free/freePoint_gbtB.env",
    "examples/halfspace/lower_halfB_grain.env",
    "examples/halfspace/upper_halfS.env",
    "examples/halfspace/upper_halfB.env",
    "examples/halfspace/lower_halfS.env",
    "examples/halfspace/vacuumB.env",
    "examples/halfspace/lower_halfB.env",
    "examples/sduct/single.env",
    "examples/sduct/sductS.env",
    "examples/sduct/sductB.env",
    "examples/sduct/sduct_nrS.env",
    "examples/sduct/sductK.env",
    "examples/sduct/sduct_bbB.env",
    "examples/sduct/sductBray.env",
    "examples/sduct/sductB_gb.env",
    "examples/sduct/sduct_bbS.env",
    "examples/sduct/sductnew.env",
    "examples/PekerisRD/PekerisRDB.env",
    "examples/BeamPattern/omni.env",
    "examples/BeamPattern/MunkKleaky.env",
    "examples/BeamPattern/shaded.env",
    "examples/BeamPattern/MunkS.env",
    "examples/BeamPattern/shadedS.env",
    "examples/MunkRot/Munk.env",
    "examples/MunkRot/MunkRot.env",
    "examples/Munk/MunkB_Coh_CervenyC.env",
    "examples/Munk/MunkB_eigenray.env",
    "examples/Munk/MunkB_geo_rot.env",
    "examples/Munk/MunkB_Coh_CervenyR.env",
    "examples/Munk/MunkB_Coh_gb.env",
    "examples/Munk/MunkS.env",
    "examples/Munk/MunkB_gbt.env",
    "examples/Munk/MunkB_Semi_gb.env",
    "examples/Munk/MunkK.env",
    "examples/Munk/MunkAnalytic.env",
    "examples/Munk/MunkB_ray.env",
    "examples/Munk/MunkSflip.env",
    "examples/Munk/MunkB_Inc.env",
    "examples/Munk/MunkB_Inc_gb.env",
    "examples/Munk/MunkB_Coh.env",
    "examples/Munk/MunkB_Coh_cpp.env",
    "examples/Munk/MunkB_gb.env",
    "examples/Munk/MunkB_ray_rot.env",
    "examples/Munk/MunkB_Semi.env",
    "examples/Munk/MunkB_Coh_SGB.env",
    "examples/Munk/MunkB_Arr.env",
    "examples/Munk/Munk_shearB.env",
    "examples/Munk/MunkB_OneBeam.env",
    "examples/Munk/Munk_shearS.env",
    "examples/Noise/ATOC/aetS_TL.env",
    "examples/Noise/ATOC/aetK_TL.env",
    "examples/Noise/ATOC/aet_VLA_K.env",
    "examples/Noise/ATOC/aetK.env",
    "examples/Noise/ATOC/aetC_TL.env",
    "examples/Noise/ATOC/aetBray.env",
    "examples/Noise/ATOC/aet_VLA_B.env",
    "examples/Noise/ATOC/aetB.env",
    "examples/Noise/ATOC/aetC.env",
    "examples/Noise/ATOC/aet_VLA_C.env",
    "examples/Noise/ATOC/aet_VLA_S.env",
    "examples/Noise/ATOC/aetS.env",
    "examples/Noise/ATOC/aetB_TL.env",
    "examples/Noise/ATOC/aetSNoiseRun.env",
    "examples/terrain/lower_half_arr.env",
    "examples/terrain/lower_half.env",
    "examples/terrain/lower_half_gbt.env",
    "examples/ParaBot/ParaBotTLGeom.env",
    "examples/ParaBot/ParaBot.env",
    "examples/ParaBot/ParaBotTLGB.env",
    "examples/PointLine/LloydSLine.env",
    "examples/PointLine/LloydPoint_gbtB.env",
    "examples/PointLine/LloydLineB.env",
    "examples/PointLine/LloydLine_gbtB.env",
    "examples/PointLine/LloydPointB.env",
    "examples/PointLine/LloydSPoint.env",
    "examples/refl.env",
    "examples/Ellipse/EllipseTLGB.env",
    "examples/Ellipse/EllipseTLGeom.env",
    "examples/Ellipse/Ellipse.env",
    "examples/SBCX/sbcx_Arr_bin.env",
    "examples/SBCX/sbcx_Arr_asc.env",
    "examples/SBCX/sbcx.env",
    "examples/Dickins/DickinsK.env",
    "examples/Dickins/DickinsFlatB.env",
    "examples/Dickins/DickinsB_oneBeam.env",
    "examples/Dickins/DickinsCervenyB.env",
    "examples/Dickins/Dickins.env",
    "examples/Dickins/DickinsFlatS.env",
    "examples/Dickins/DickinsBray.env",
    "examples/Dickins/DickinsFlatBray.env",
    "examples/Dickins/DickinsFlatK.env",
    "examples/Dickins/DickinsB.env",
    "examples/Dickins/March/DickinsK.env",
    "examples/Dickins/March/DickinsK_rd.env",
    "examples/Dickins/Precalc/DickinsK.env",
    "examples/Dickins/Precalc/DickinsK_rd.env",
    "examples/MunkTS/MunkB.env",
    "examples/MunkTS/MunkS.env",
    "examples/block/blockB_ray.env",
    "examples/block/blockB_gb.env",
    "examples/block/blockB_geo.env",
    ])
def test_examples_2e(envfile, init_csv):
    start = time.perf_counter()
    status = "PASS"
    try:
        env = bh.Environment.from_file(envfile)
        results1 = bh.compute(env)
        results2 = bh.compute_from_file("bellhop", env["_from_file"])
        pdt.assert_frame_equal(results1["results"], results2["results"])
    except Exception as e:
        status = f"FAIL ({type(e).__name__})"
        raise
    finally:
        elapsed = round(time.perf_counter() - start, 3)
        with open(RESULTS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([envfile, elapsed, status])

