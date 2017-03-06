# UnityPack
[![Build Status](https://api.travis-ci.org/HearthSim/UnityPack.svg?branch=master)](https://travis-ci.org/HearthSim/UnityPack)

A library to deserialize Unity3D Assets and AssetBundles files (*.unity3d).

## Dependencies

* [python-lz4](https://github.com/python-lz4/python-lz4) (For UnityFS-compressed files)


## How Unity packs assets

Most extractors for Unity3D files (such as [Disunity](https://github.com/ata4/disunity))
deal with the format as a "file store", treating it as one would treat a zip. This is
not how the format actually works.

Unity files are binary-packed, serialized collections of Unity3D classes. To this end,
they are much closer to a json file containing arrays of objects.

Some of those classes have fields which contain raw data, such as Texture2D's `image data`
field or TextAsset's `m_Script` field. Using this, files can be "extracted" from the asset
bundles by using their `m_Name` and an appropriate extension. But doing so leaves out all
the "unextractable" classes which one might want to deal with.


## Usage

To open an asset, or asset bundle, with unitypack:

```py
import unitypack

with open("example.unity3d", "rb") as f:
	bundle = unitypack.load(f)

	for asset in bundle.assets:
		print("%s: %s:: %i objects" % (bundle, asset, len(asset.objects)))
```

The `objects` field on every `Asset` is a dictionary of `path_id` keys to `ObjectInfo`
values. The `path_id` is a unique 64-bit signed int which represents the object instance.
The `ObjectInfo` class is a lazy lookup for the data on that object.

Thus, if you want to actually extract the data:

```py
for id, object in asset.objects.items():
	# Let's say we only want TextAsset objects
	if object.type == "TextAsset":
		# We avoid reading the data, unless it's a TextAsset
		data = object.read()
		# The resulting `data` is a unitypack.engine.TextAsset instance
		print("Asset name:", data.name)
		print("Contents:", repr(data.script))
```

Not all base Unity3D classes are implemented. If a class is unimplemented, or a custom class
(eg. a non-Unity class) is encountered, the resulting data is a dict of the fields instead.
The same dict of fields can be found in the `_obj` attribute of the instance, otherwise.


## Included tools

Included are two scripts which use unitypack for some common operations:


### Asset extraction

`unityextract` can extract common types of data from assets and asset bundles, much like Disunity.
By default, it will extract all known extractable types:

* `AudioClip` objects will be converted back to their original format. Note that recent Unity3D
  versions pack these as FSB files, so [python-fsb5](https://github.com/hearthsim/python-fsb5)
  is required to convert them back.
* `Texture2D` objects will be converted to png files. Not all Texture2D formats are supported.
  [Pillow](https://github.com/python-pillow/Pillow) version >= 3.4 is required for this.
  [decrunch](https://github.com/HearthSim/decrunch) is required for DXT1Crunched / DXT5Crunched.
* `Mesh` objects (3D objects) will be pickled. Pull requests implementing a .obj converter are
  welcome and wanted.
* `TextAsset` objects will be extracted as plain text, to .txt files
* `Shader` objects work essentially the same way as TextAsset objects, but will be extracted to
  .cg files.

Filters for individual formats are available. Run `unityextract --help` for the full list.


### YAML conversion

`unity2yaml` can convert AssetBundles to YAML output. YAML is more appropriate than JSON
due to the recursive, pointer-heavy and class-heavy nature of the Unity3D format.

When run with the `--strip` argument, extractable data will be stripped out. This can make the
resulting YAML output far less heavy, as binary data will otherwise be converted to Base64 which
can result in extremely large text output.

Here is a stripped example of the `movies0.unity3d` file from Hearthstone, which contains only
two objects (a MovieTexture cinematic and a corresponding AudioClip):

```yaml
!unitypack:AudioClip
m_BitsPerSample: 16
m_Channels: 0
m_CompressionFormat: 0
m_Frequency: 0
m_IsTrackerFormat: false
m_Legacy3D: false
m_Length: 0.0
m_LoadInBackground: false
m_LoadType: 0
m_Name: Cinematic audio
m_PreloadAudioData: true
m_Resource: !unitypack:StreamedResource {m_Offset: 0, m_Size: 0, m_Source: ''}
m_SubsoundIndex: 0

m_AssetBundleName: ''
m_Container:
- first: final/data/movies/cinematic.unity3d
  second:
    asset: !PPtr [0, -4923783912342650895]
    preloadIndex: 0
    preloadSize: 2
m_Dependencies: []
m_IsStreamedSceneAssetBundle: false
m_MainAsset: {asset: null, preloadIndex: 0, preloadSize: 0}
m_Name: ''
m_PreloadTable:
- !PPtr [0, -6966092991433622133]
- !PPtr [0, -4923783912342650895]
m_RuntimeCompatibility: 1

!unitypack:stripped:MovieTexture
m_AudioClip: !PPtr [0, -6966092991433622133]
m_ColorSpace: 1
m_Loop: false
m_MovieData: <stripped>
m_Name: Cinematic
```

Stripped classes will be prefixed with `unitypack:stripped:`.


## License

python-unitypack is licensed under the terms of the MIT license.
The full license text is available in the `LICENSE` file.


## Community

python-unitypack is a [HearthSim](http://hearthsim.info) project. All development
happens on our IRC channel `#hearthsim` on [Freenode](https://freenode.net).

Contributions are welcome. Make sure to read through the `CONTRIBUTING.md` first.
