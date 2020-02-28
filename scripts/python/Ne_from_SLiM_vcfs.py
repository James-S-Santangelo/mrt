#!/usr/bin/env python3.6

# Script takes a directory filled with VCFs exported from SLiM and
# for each one, uses the site-frequency spectrum to calculate Ne
# from both Watterson and Pi. Exports results as single CSV.

import csv
import argparse

from glob import glob
from cyvcf2 import VCF
from tqdm import tqdm

import SFS as SFS
from create_output_directory import create_output_directory


def create_sfs_dict(inpath):

    print("Creating dictionary of Site Frequency Sprectra from VCFs in {0}".format(inpath))

    # Initialize sfs dict
    sfs_dict = {}

    # Get files from inpath
    files = glob(inpath + "**/*.vcf.gz", recursive=True)

    total_vcfs = 0
    for vcf in tqdm(files):

        # Load in VCF file
        my_vcf = VCF(vcf)

        #     # Split VCF filename and split to extract population size, bottleneck and generation
        split_filename = vcf.split('/')[-1].split('_')
        N_sims = int(split_filename[0].split('N')[1])
        bot = float(split_filename[1].split('bot')[1])
        gen = int(split_filename[2].split('gen')[1].split('.')[0])
        # print(N_sims, bot, gen)
        N_samples = len(my_vcf.samples)

        # Initialize list for sfs
        sfs_list = [0] * ((2 * N_samples) + 1)

        # Add singletons, doubletons, ...n-tons
        for variant in my_vcf:
            AC = variant.INFO.get('AC')
            sfs_list[AC] += 1

        # Add invariant sites to sfs list
        ch_length = 1e8
        sfs_list[0] = int(ch_length - sum(sfs_list))
        # print(sfs_list)

        # Use sfs list to instantiate SFS class (Rob's code)
        sfs = SFS.SFS(sfs_list)

        # Create string for dictionary key
        l1 = str(N_sims) + '-' + str(bot)

        # Add SFS class instances to appropriate dictionary keys.
        if l1 in sfs_dict:
            sfs_dict[l1][gen] = sfs
        else:
            sfs_dict[l1] = {gen: sfs}

        total_vcfs += 1

    print("Processed {0} VCFs".format(total_vcfs))

    return sfs_dict


def write_thetaNe_values(sfs_dict, outpath):

    print("Writing diversity (i.e., theta) summary statistics to CSV")

    # Open csv to write resutls
    filepath = outpath + 'theta_NeValues.csv'
    with open(filepath, 'w+') as f:

        # Instantiate CSV writer
        writer = csv.writer(f)

        # Write header
        header = ['N', 'bot', 'gen', 'theta_pi', 'theta_w', 'Ne_pi', 'Ne_w', '\n']
        writer.writerow(header)

        mu = float(1e-8)

        # Interate through sfs dictionary and write to csv
        for key in tqdm(sfs_dict.keys()):

            # Get dict values, which are encoded as <pop size>-<bottleneck>
            size_bot = sfs_dict[key]

            # Get generations as list
            generations = sorted(size_bot.keys())

            # Iterate through nested dictionary values (generations)
            for gen in generations:
                pi = size_bot[gen].theta_pi()
                wattersons = size_bot[gen].theta_w()
                Ne_pi = round((pi / (4 * mu)), 3)
                Ne_w = round((wattersons / (4 * mu)), 3)
                pop_size = key.split('-')[0]
                bottleneck = key.split('-')[1]

                # Write generation's summary stats as row
                row = [pop_size, bottleneck, gen, pi, wattersons, Ne_pi, Ne_w, '\n']
                writer.writerow(row)

    print("Done writing summary stats. Output written to {0}".format(filepath))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inpath", help="Path to directory with VCFs", type=str)
    parser.add_argument("-o", "--outpath", help="Path to which CSV with summary stats should be written", type=str)
    args = parser.parse_args()

    # Retrieve command-line arguments
    inpath = args.inpath
    outpath = args.outpath

    # Create output directory, if it doesn't exit
    create_output_directory(outpath)

    # Create SFS dict
    sfs_dict = create_sfs_dict(inpath=inpath)

    # Create summary CSV
    write_thetaNe_values(sfs_dict=sfs_dict, outpath=outpath)
