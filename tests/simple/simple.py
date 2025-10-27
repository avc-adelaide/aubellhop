
import bellhop as bh

env = bh.Environment.from_file("simple_neg_ssp")
tl = bh.compute_transmission_loss(env)

