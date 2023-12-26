from struct import unpack, calcsize
from sys import argv
from os import SEEK_SET, makedirs
from dataclasses import dataclass


SUBDIR = 'extracted'

@dataclass
class BPB:
    sig_jmp: str
    oem_ident: str
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sectors: int
    dir_ent_count: int
    total_sectors: int
    mdt: int
    sectors_per_fat: int
    sectors_per_track: int
    heads_count: int
    hidden_sectors: int
    larg_sector_count: int

    def __init__(self, file):
        format = '<3s8sHBHBHHBHHHII'
        (
            self.sig_jmp,
            self.oem_ident,
            self.bytes_per_sector,
            self.sectors_per_cluster,
            self.reserved_sectors,
            self.number_of_fat,
            self.dir_ent_count,
            self.total_sectors,
            self.mdt,
            self.sectors_per_fat,
            self.sectors_per_track,
            self.heads_count,
            self.hidden_sectors,
            self.larg_sector_count
        ) = unpack(format, file.read(calcsize(format)))

@dataclass
class EBR:
    drive_number: int
    win_nt_reserved: int
    sig: int
    volume_id: str
    volume_label: str
    ident_string: str

    def __init__(self, file):
        format = '<BBB4s11s8s'
        (
            self.drive_number,
            self.win_nt_reserved,
            self.sig,
            self.volume_id,
            self.volume_label,
            self.ident_string
        ) = unpack(format, file.read(calcsize(format)))

@dataclass
class DIR:
    filename: str
    attrs: int
    reserved_nt: int
    tenth_creation: int
    creation_time: int
    date_creation: int
    last_accessed: int
    first_cluter_zero: int
    last_modification_time: int
    last_modification_date: int
    low_cluster: int
    file_size: int

    def __init__(self, file):
        format = '<11sBBBHHHHHHHI'
        (
            self.filename,
            self.attrs,
            self.reserved_nt,
            self.tenth_creation,
            self.creation_time,
            self.date_creation,
            self.last_accessed,
            self.first_cluter_zero,
            self.last_modification_time,
            self.last_modification_date,
            self.low_cluster,
            self.file_size
        ) = unpack(format, file.read(calcsize(format)))

def read_file(image, file, bpb, fat_offset, data_offset):
    if file.filename[0] in (0, 0xe5): return
    filename = file.filename.decode().strip()

    active_cluster = file.low_cluster
    file_size = file.file_size

    out_file = open(SUBDIR + '/' + filename, 'wb')

    block_size = bpb.sectors_per_cluster * bpb.bytes_per_sector
    while active_cluster < 0xffe:
        lba = data_offset + (active_cluster - 2) * bpb.sectors_per_cluster
        image.seek(lba * bpb.bytes_per_sector, SEEK_SET)
        buffer = image.read(block_size if file_size >= block_size else file_size)
        out_file.write(buffer)
        file_size -= len(buffer)
        fat_index = active_cluster * 3 // 2
        image.seek(fat_offset * bpb.bytes_per_sector + fat_index, SEEK_SET)

        tmp = int.from_bytes(image.read(2), 'little')
        if active_cluster % 2 == 0: active_cluster = tmp & 0x0FFF
        else: active_cluster = tmp >> 4
    out_file.close()

def main():
    makedirs(SUBDIR, exist_ok=True)
    image = open(argv[1], 'rb')
    bpb = BPB(image)
    ebr = EBR(image)
    print(bpb)
    print(ebr)

    fat_offset = bpb.reserved_sectors
    dir_entry_offset = fat_offset + bpb.sectors_per_fat * bpb.number_of_fat

    tmp = dir_entry_offset * bpb.bytes_per_sector + 32 * bpb.dir_ent_count
    if tmp % bpb.bytes_per_sector == 0: data_offset = tmp // bpb.bytes_per_sector
    else: data_offset = tmp // bpb.bytes_per_sector + 1

    image.seek(dir_entry_offset * bpb.bytes_per_sector, SEEK_SET)
    entries = [DIR(image) for _ in range(bpb.dir_ent_count)]
    for file in entries:
        read_file(image, file, bpb, fat_offset, data_offset)


main()
