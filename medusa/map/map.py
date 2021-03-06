#*_* coding=utf8 *_*
#!/usr/bin/env python

import zlib
import struct
try:
    from CStringIO import CStringIO as StringIO
except:
    from StringIO import StringIO

from medusa.utils.fields import FieldsClass, FieldsSerializer

"""
读取和保存地图文件，此文件格式和数据结构和《斗破苍穹》的游戏地图一样的，
请参照具体格式请参照服务端中的地图设计，对map文件格式的分析。

作者：唐万万
日期：2013-10-18
"""

class TiledMap(FieldsClass):

    """ 地图 """

    __fields__ = {
        "map_id": 0,
        "map_type": 1,
        "map_name": 'untitled',
        "map_picture": '',
        "tile_row": 0,
        "tile_col": 0,
        "element_num": 0,
        "jump_point_num": 0,
        "offset_x": 0,
        "offset_y": 0,
        "tw": 20,
        "th": 20,

        "tiles": [],
        "elements": [],
        "jump_points": []
    }

    def resize_tiles(self, tile_col, tile_row):
        """ 重置tiles的大小 """

        if tile_col < 0 or tile_row < 0:
            return

        new_tiles = []
        for x in xrange(0, tile_col):
            for y in xrange(0, tile_row):
                if x < self.tile_col and y < self.tile_row:
                    tile = self.get_tile(x, y)
                else:
                    tile = MapTile()
                
                new_tiles.append(tile)

        self.tile_col = tile_col
        self.tile_row = tile_row
        self.tiles = new_tiles

    def get_tile(self, x, y):
        """ 获取指定位置的tile """
        return self.tiles[self.tile_row * x + y]


class MapTile(FieldsClass):

    """ 地图坐标格子 """

    __fields__ = {
        "reversed": False,
        "arena": False,
        "sell": False,
        "all_safe": False,
        "safe": False,
        "run": False,
        "alpha": False,
        "exist": False,
    }

    @classmethod
    def from_byte(cls, byteval):
        def get_bit(byteval, idx):
            return ((byteval & (1 << idx)) != 0)

        tile = cls()
        tile.update_fields(
            exist=get_bit(byteval, 0),
            alpha=get_bit(byteval, 1),
            run=get_bit(byteval, 2),
            safe=get_bit(byteval, 3),
            all_safe=get_bit(byteval, 4),
            sell=get_bit(byteval, 5),
            arena=get_bit(byteval, 6),
            reversed=get_bit(byteval, 7)
        )

        return tile

    def to_byte(self):
        bits = (self.exist,
                self.alpha,
                self.run,
                self.safe,
                self.all_safe,
                self.sell,
                self.arena,
                self.reversed)

        byteval, pos = 0, 0
        for bit in bits:
            bitval = 1 if bit else 0
            byteval += bitval << pos
            pos += 1

        return byteval

    def __repr__(self):
        return str(self.to_byte())


class MapElement(FieldsClass):

    """ 地图元素(怪物,NPC等) """

    __fields__ = {
        "id": None,
        "index_tx": None,
        "index_ty": None,
        "type": None,
        "data_length": None,
        "data": ''
    }


class MapJumpPoint(FieldsClass):

    """ 地图跳转点 """

    __fields__ = {
        "id": None,
        "index_tx": None,
        "index_ty": None,
        "target_map_id": None,
        "target_index_tx": None,
        "target_index_ty": None,
        "hw": None,
        "yl": None,
        "wl": None,
        "min_level": None,
        "max_level": None,
        "data_length": None,
        "data": ''
    }

class TiledMapSerializer(FieldsSerializer):

    """ Map文件序列化和反序列化 """

    header_fields_desc = [
        ("map_id", "!i", 4),
        ("map_type", "!i", 4),
        ("map_name", None, 32, 'gb2312'),
        ("map_picture", None, 32, 'gb2312'),
        ("tile_col", "!i", 4),
        ("tile_row", "!i", 4),
        ("element_num", "!i", 4),
        ("jump_point_num", "!i", 4),
        ("offset_x", "!i", 4),
        ("offset_y", "!i", 4),
        ("tw", "!i", 4),
        ("th", "!i", 4),
    ]

    element_header_fields_desc = [
        ("id", "!i", 4),
        ("index_tx", "!i", 4),
        ("index_ty", "!i", 4),
        ("type", "!i", 4),
        ("data_length", "!i", 4),
    ]

    jump_point_header_fields_desc = [
        ("id", "!i", 4),
        ("index_tx", "!i", 4),
        ("index_ty", "!i", 4),
        ("target_map_id", "!i", 4),
        ("target_index_tx", "!i", 4),
        ("target_index_ty", "!i", 4),
        ("hw", "!i", 4),
        ("yl", "!i", 4),
        ("wl", "!i", 4),
        ("min_level", "!i", 4),
        ("max_level", "!i", 4),
        ("data_length", "!i", 4),
    ]

    def read_from_file(self, file_path):
        """ 读取并解析map文件 """

        with open(file_path, 'rb') as f:
            compressed_bin = f.read()

        raw_binary = zlib.decompress(compressed_bin)
        tiled_map_stream = StringIO(raw_binary)

        tiled_map = TiledMap()

        # 读取Header部分
        header_stream = StringIO(tiled_map_stream.read(104))
        header_fields = self.parse_fields(
            header_stream, self.header_fields_desc)
        tiled_map.update_fields(**header_fields)

        # 读取tiles部分
        tiles = []
        tile_length = tiled_map.tile_row * tiled_map.tile_col
        tile_stream = StringIO(tiled_map_stream.read(tile_length))

        for i in xrange(0, tiled_map.tile_row * tiled_map.tile_col):
            tile_byte = struct.unpack('b', tile_stream.read(1))[0]
            tile = MapTile.from_byte(tile_byte)
            tiles.append(tile)

        tiled_map.tiles = tiles

        # 读取elements部分
        for i in xrange(0, tiled_map.element_num):
            element = MapElement()
            element_header_stream = StringIO(tiled_map_stream.read(20))
            element_fields = self.parse_fields(
                element_header_stream,
                self.element_header_fields_desc)

            element.update_fields(**element_fields)
            if element.data_length > 0:
                element.data = tiled_map_stream.read(element.data_length)
            else:
                element.data = ''

            tiled_map.elements.append(element)

        # 读取jump elements部分
        for i in xrange(0, tiled_map.jump_point_num):
            jump_point = MapJumpPoint()
            jump_point_header_stream = StringIO(tiled_map_stream.read(48))

            jump_point_fields = self.parse_fields(
                jump_point_header_stream,
                self.jump_point_header_fields_desc)

            jump_point.update_fields(**jump_point_fields)
            if jump_point.data_length > 0:
                jump_point.data = tiled_map_stream.read(jump_point.data_length)

            tiled_map.jump_points.append(jump_point)

        return tiled_map

    def dump_to_stream(self, tiled_map, tiled_map_stream):
        """ 将tiled_map保存在给定的流中 """

        # 写入Header部分
        tiled_map_fields = tiled_map.get_fields()
        self.dump_fields(tiled_map_stream, tiled_map_fields, self.header_fields_desc)

        # 写入Tiles部分
        tile_num = tiled_map.tile_row * tiled_map.tile_col
        assert len(tiled_map.tiles) == tile_num
        for tile in tiled_map.tiles:
            tile_byte = struct.pack('b', tile.to_byte())
            tiled_map_stream.write(tile_byte)

        # 写入Elements部分
        assert len(tiled_map.elements) == tiled_map.element_num
        for element in tiled_map.elements:
            element_fields = element.get_fields()
            self.dump_fields(
                tiled_map_stream, element_fields, self.element_header_fields_desc)

            assert len(element.data) == element.data_length
            tiled_map_stream.write(element.data)

        # 写入JumpPoint部分
        assert len(tiled_map.jump_points) == tiled_map.jump_point_num
        for jump_point in tiled_map.jump_points:
            jump_point_fields = jump_point.get_fields()
            self.dump_fields(
                tiled_map_stream, jump_point_fields, self.jump_point_header_fields_desc)

            assert len(jump_point.data) == jump_point.data_length
            tiled_map_stream.write(jump_point.data)

        return tiled_map_stream

    def dump_to_file(self, tiled_map, file_path):
        """ 将tiled_map保存在给定的文件中 """

        tiled_map_stream = StringIO()
        self.dump_to_stream(tiled_map, tiled_map_stream)

        tiled_map_stream.seek(0)
        compressed_bin = zlib.compress(tiled_map_stream.read())
        with open(file_path, 'wb') as f:
            f.write(compressed_bin)
