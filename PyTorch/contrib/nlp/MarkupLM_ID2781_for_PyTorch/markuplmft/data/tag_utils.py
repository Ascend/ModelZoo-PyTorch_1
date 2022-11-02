# ============================================================================
# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the BSD 3-Clause License  (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

tags_dict = {'a': 0, 'abbr': 1, 'acronym': 2, 'address': 3, 'altGlyph': 4, 'altGlyphDef': 5, 'altGlyphItem': 6,
             'animate': 7, 'animateColor': 8, 'animateMotion': 9, 'animateTransform': 10, 'applet': 11, 'area': 12,
             'article': 13, 'aside': 14, 'audio': 15, 'b': 16, 'base': 17, 'basefont': 18, 'bdi': 19, 'bdo': 20,
             'bgsound': 21, 'big': 22, 'blink': 23, 'blockquote': 24, 'body': 25, 'br': 26, 'button': 27, 'canvas': 28,
             'caption': 29, 'center': 30, 'circle': 31, 'cite': 32, 'clipPath': 33, 'code': 34, 'col': 35,
             'colgroup': 36, 'color-profile': 37, 'content': 38, 'cursor': 39, 'data': 40, 'datalist': 41, 'dd': 42,
             'defs': 43, 'del': 44, 'desc': 45, 'details': 46, 'dfn': 47, 'dialog': 48, 'dir': 49, 'div': 50, 'dl': 51,
             'dt': 52, 'ellipse': 53, 'em': 54, 'embed': 55, 'feBlend': 56, 'feColorMatrix': 57,
             'feComponentTransfer': 58, 'feComposite': 59, 'feConvolveMatrix': 60, 'feDiffuseLighting': 61,
             'feDisplacementMap': 62, 'feDistantLight': 63, 'feFlood': 64, 'feFuncA': 65, 'feFuncB': 66, 'feFuncG': 67,
             'feFuncR': 68, 'feGaussianBlur': 69, 'feImage': 70, 'feMerge': 71, 'feMergeNode': 72, 'feMorphology': 73,
             'feOffset': 74, 'fePointLight': 75, 'feSpecularLighting': 76, 'feSpotLight': 77, 'feTile': 78,
             'feTurbulence': 79, 'fieldset': 80, 'figcaption': 81, 'figure': 82, 'filter': 83, 'font-face-format': 84,
             'font-face-name': 85, 'font-face-src': 86, 'font-face-uri': 87, 'font-face': 88, 'font': 89, 'footer': 90,
             'foreignObject': 91, 'form': 92, 'frame': 93, 'frameset': 94, 'g': 95, 'glyph': 96, 'glyphRef': 97,
             'h1': 98, 'h2': 99, 'h3': 100, 'h4': 101, 'h5': 102, 'h6': 103, 'head': 104, 'header': 105, 'hgroup': 106,
             'hkern': 107, 'hr': 108, 'html': 109, 'i': 110, 'iframe': 111, 'image': 112, 'img': 113, 'input': 114,
             'ins': 115, 'kbd': 116, 'keygen': 117, 'label': 118, 'legend': 119, 'li': 120, 'line': 121,
             'linearGradient': 122, 'link': 123, 'main': 124, 'map': 125, 'mark': 126, 'marker': 127, 'marquee': 128,
             'mask': 129, 'math': 130, 'menu': 131, 'menuitem': 132, 'meta': 133, 'metadata': 134, 'meter': 135,
             'missing-glyph': 136, 'mpath': 137, 'nav': 138, 'nobr': 139, 'noembed': 140, 'noframes': 141,
             'noscript': 142, 'object': 143, 'ol': 144, 'optgroup': 145, 'option': 146, 'output': 147, 'p': 148,
             'param': 149, 'path': 150, 'pattern': 151, 'picture': 152, 'plaintext': 153, 'polygon': 154,
             'polyline': 155, 'portal': 156, 'pre': 157, 'progress': 158, 'q': 159, 'radialGradient': 160, 'rb': 161,
             'rect': 162, 'rp': 163, 'rt': 164, 'rtc': 165, 'ruby': 166, 's': 167, 'samp': 168, 'script': 169,
             'section': 170, 'select': 171, 'set': 172, 'shadow': 173, 'slot': 174, 'small': 175, 'source': 176,
             'spacer': 177, 'span': 178, 'stop': 179, 'strike': 180, 'strong': 181, 'style': 182, 'sub': 183,
             'summary': 184, 'sup': 185, 'svg': 186, 'switch': 187, 'symbol': 188, 'table': 189, 'tbody': 190,
             'td': 191, 'template': 192, 'text': 193, 'textPath': 194, 'textarea': 195, 'tfoot': 196, 'th': 197,
             'thead': 198, 'time': 199, 'title': 200, 'tr': 201, 'track': 202, 'tref': 203, 'tspan': 204, 'tt': 205,
             'u': 206, 'ul': 207, 'use': 208, 'var': 209, 'video': 210, 'view': 211, 'vkern': 212, 'wbr': 213,
             'xmp': 214}
