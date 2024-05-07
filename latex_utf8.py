"""Conversion map and functions between UTF-8 and LaTeX characters.
From data found at https://www.ctan.org/tex-archive/support/utf2any/maps
"""

def from_latex_to_utf8(value):
    "Convert string value from LaTeX notation to UTF-8 characters."
    stack = []
    result = []
    for pos, c in enumerate(value):
        if c == "{":
            stack.append(pos)
        elif c == "}":
            if len(stack) == 1:
                item = value[stack[0]:pos+1]
                if item.startswith(r"{\v "):
                    item = r"{\v{" + item[4:] + "}"
                result.append(map_latex_to_utf8.get(item[1:-1], item))
            stack.pop()
        elif not stack:
            result.append(c)
    return "".join(result)
    
def from_utf8_to_latex(value):
    "Convert string value from UTF-8 characters to LaTeX notation."
    result = []
    for c in value:
        try:
            result.append("{" + map_utf8_to_latex[c] + "}")
        except KeyError:
            result.append(c)
    return "".join(result)


table = [
    ("\u00a0", r"~"),
    ("\u00a1", r"!`"),
    ("\u00a2", r"\textcent{}"),
    ("\u00a3", r"\pounds{}"),
    ("\u00a4", r"\textcurrency{}"),
    ("\u00a5", r"\textyen{}"),
    ("\u00a6", r"\textbrokenbar{}"),
    ("\u00a7", r"\S{}"),
    ("\u00a8", r"\textasciidieresis{}"),
    ("\u00a9", r"\copyright{}"),
    ("\u00aa", r"\textordfeminine{}"),
    ("\u00ab", r"\guillemotleft{}"),
    ("\u00ac", r"\textlnot{}"),
    ("\u00ad", r"-"),
    ("\u00ae", r"\textregistered{}"),
    ("\u00af", r"\textmacron{}"),
    ("\u00b0", r"\textdegree{}"),
    ("\u00b1", r"\textpm{}"),
    ("\u00b2", r"\texttwosuperior{}"),
    ("\u00b3", r"\textthreesuperior{}"),
    ("\u00b4", r"\textasciiacute{}"),
    ("\u00b5", r"\textmu{}"),
    ("\u00b6", r"\P{}"),
    ("\u00b7", r"\textperiodcentered{}"),
    ("\u00b8", r"\c{"),
    ("\u00b9", r"\textonesuperior{}"),
    ("\u00ba", r"\textordmasculine{}"),
    ("\u00bb", r"\guillemotright{}"),
    ("\u00bc", r"\ensuremath{{}^1\!/\!_4}"),
    ("\u00bd", r"\ensuremath{{}^1\!/\!_2}"),
    ("\u00be", r"\ensuremath{{}^3\!/\!_4}"),
    ("\u00bf", r"?`"),
    ("\u00c0", r"\`A"),
    ("\u00c1", r"\'A"),
    ("\u00c2", r"\^A"),
    ("\u00c3", r"\~A"),
    ("\u00c4", r"\"A"),
    ("\u00c5", r"\AA{}"),
    ("\u00c6", r"\AE{}"),
    ("\u00c7", r"\c{C}"),
    ("\u00c8", r"\`E"),
    ("\u00c9", r"\'E"),
    ("\u00ca", r"\^E"),
    ("\u00cb", r"\"E"),
    ("\u00cc", r"\`I"),
    ("\u00cd", r"\'I"),
    ("\u00ce", r"\^I"),
    ("\u00cf", r"\"I"),
    ("\u00d0", r"\DH{}"),
    ("\u00d1", r"\~N"),
    ("\u00d2", r"\`O"),
    ("\u00d3", r"\'O"),
    ("\u00d4", r"\^O"),
    ("\u00d5", r"\~O"),
    ("\u00d6", r"\"O"),
    ("\u00d7", r"\texttimes{}"),
    ("\u00d8", r"\O{}"),
    ("\u00d9", r"\`U"),
    ("\u00da", r"\'U"),
    ("\u00db", r"\^U"),
    ("\u00dc", r"\"U"),
    ("\u00dd", r"\'Y"),
    ("\u00de", r"\TH{}"),
    ("\u00df", r"\ss{}"),
    ("\u00e0", r"\`a"),
    ("\u00e1", r"\'a"),
    ("\u00e2", r"\^a"),
    ("\u00e3", r"\~a"),
    ("\u00e4", r"\"a"),
    ("\u00e5", r"\aa{}"),
    ("\u00e6", r"\ae{}"),
    ("\u00e7", r"\c{c}"),
    ("\u00e8", r"\`e"),
    ("\u00e9", r"\'e"),
    ("\u00ea", r"\^e"),
    ("\u00eb", r"\"e"),
    ("\u00ec", r"\`{\i}"),
    ("\u00ed", r"\'{\i}"),
    ("\u00ee", r"\^{\i}"),
    ("\u00ef", r"\"{\i}"),
    ("\u00f0", r"\dh{}"),
    ("\u00f1", r"\~n"),
    ("\u00f2", r"\`o"),
    ("\u00f3", r"\'o"),
    ("\u00f4", r"\^o"),
    ("\u00f5", r"\~o"),
    ("\u00f6", r"\"o"),
    ("\u00f7", r"\textdiv{}"),
    ("\u00f8", r"\o{}"),
    ("\u00f9", r"\`u"),
    ("\u00fa", r"\'u"),
    ("\u00fb", r"\^u"),
    ("\u00fc", r"\"u"),
    ("\u00fd", r"\'y"),
    ("\u00fe", r"\th{}"),
    ("\u00ff", r"\"y"),
    ("\u0100", r"\=A"),
    ("\u0101", r"\=a"),
    ("\u0102", r"\u{A}"),
    ("\u0103", r"\u{a}"),
    ("\u0104", r"\textpolhook{A}"),
    ("\u0105", r"\textpolhook{a}"),
    ("\u0106", r"\'C"),
    ("\u0107", r"\'c"),
    ("\u0108", r"\^C"),
    ("\u0109", r"\^c"),
    ("\u010a", r"\.C"),
    ("\u010b", r"\.c"),
    ("\u010c", r"\v{C}"),
    ("\u010d", r"\v{c}"),
    ("\u010e", r"\v{D}"),
    ("\u010f", r"\v{d}"),
    ("\u0110", r"\DJ{}"),
    ("\u0111", r"\dj{}"),
    ("\u0112", r"\=E"),
    ("\u0113", r"\=e"),
    ("\u0114", r"\u{E}"),
    ("\u0115", r"\u{e}"),
    ("\u0116", r"\.E"),
    ("\u0117", r"\.e"),
    ("\u0118", r"\textpolhook{E}"),
    ("\u0119", r"\textpolhook{e}"),
    ("\u011a", r"\v{E}"),
    ("\u011b", r"\v{e}"),
    ("\u011c", r"\^G"),
    ("\u011d", r"\^g"),
    ("\u011e", r"\u{G}"),
    ("\u011f", r"\u{g}"),
    ("\u0120", r"\.G"),
    ("\u0121", r"\.g"),
    ("\u0122", r"\c{G}"),
    ("\u0123", r"\c{g}"),
    ("\u0124", r"\^H"),
    ("\u0125", r"\^h"),
    ("\u0127", r"\textcrh{}"),
    ("\u0128", r"\~I"),
    ("\u0129", r"\~{\i}"),
    ("\u012a", r"\=I"),
    ("\u012b", r"\={\i}"),
    ("\u012c", r"\u{I}"),
    ("\u012d", r"\u{\i}"),
    ("\u012e", r"\textpolhook{I}"),
    ("\u012f", r"\textpolhook{\i}"),
    ("\u0130", r"\.I"),
    ("\u0131", r"\i{}"),
    ("\u0132", r"IJ"),
    ("\u0133", r"ij"),
    ("\u0134", r"\^J"),
    ("\u0135", r"\^{\j}"),
    ("\u0136", r"\c{K}"),
    ("\u0137", r"\c{k}"),
    ("\u0139", r"\'L"),
    ("\u013a", r"\'l"),
    ("\u013b", r"\c{L}"),
    ("\u013c", r"\c{l}"),
    ("\u013d", r"\v{L}"),
    ("\u013e", r"\v{l}"),
    ("\u013f", r"L\ensuremath{\cdot}"),
    ("\u0140", r"l\ensuremath{\cdot}"),
    ("\u0141", r"\L{}"),
    ("\u0142", r"\l{}"),
    ("\u0143", r"\'N"),
    ("\u0144", r"\'n"),
    ("\u0145", r"\c{N}"),
    ("\u0146", r"\c{n}"),
    ("\u0147", r"\v{N}"),
    ("\u0148", r"\v{n}"),
    ("\u0149", r"'n"),
    ("\u014a", r"\NG{}"),
    ("\u014b", r"\ng{}"),
    ("\u014c", r"\=O"),
    ("\u014d", r"\=o"),
    ("\u014e", r"\u{O}"),
    ("\u014f", r"\u{o}"),
    ("\u0150", r"\H{O}"),
    ("\u0151", r"\H{o}"),
    ("\u0152", r"\OE{}"),
    ("\u0153", r"\oe{}"),
    ("\u0154", r"\'R"),
    ("\u0155", r"\'r"),
    ("\u0156", r"\c{R}"),
    ("\u0157", r"\c{r}"),
    ("\u0158", r"\v{R}"),
    ("\u0159", r"\v{r}"),
    ("\u015a", r"\'S"),
    ("\u015b", r"\'s"),
    ("\u015c", r"\^S"),
    ("\u015d", r"\^s"),
    ("\u015e", r"\c{S}"),
    ("\u015f", r"\c{s}"),
    ("\u0160", r"\v{S}"),
    ("\u0161", r"\v{s}"),
    ("\u0162", r"\c{T}"),
    ("\u0163", r"\c{t}"),
    ("\u0164", r"\v{T}"),
    ("\u0165", r"\v{t}"),
    ("\u0168", r"\~U"),
    ("\u0169", r"\~u"),
    ("\u016a", r"\=U"),
    ("\u016b", r"\=u"),
    ("\u016c", r"\u{U}"),
    ("\u016d", r"\u{u}"),
    ("\u016e", r"\r{U}"),
    ("\u016f", r"\r{u}"),
    ("\u0170", r"\H{U}"),
    ("\u0171", r"\H{u}"),
    ("\u0172", r"\textpolhook{U}"),
    ("\u0173", r"\textpolhook{u}"),
    ("\u0174", r"\^W"),
    ("\u0175", r"\^w"),
    ("\u0176", r"\^Y"),
    ("\u0177", r"\^y"),
    ("\u0178", r"\"Y"),
    ("\u0179", r"\'Z"),
    ("\u017a", r"\'z"),
    ("\u017b", r"\.Z"),
    ("\u017c", r"\.z"),
    ("\u017d", r"\v{Z}"),
    ("\u017e", r"\v{z}"),
    ("\u0180", r"\textcrb{}"),
    ("\u0192", r"\textit{f}"),
    ("\u0194", r"\textgamma{}"),
    ("\u0195", r"\texthvlig{}"),
    ("\u0197", r"\ipabar{I}{.6ex}{1.1}{}{}"),
    ("\u019a", r"\textbarl{}"),
    ("\u019b", r"\textcrlambda{}"),
    ("\u01b5", r"\ipabar{Z}{.7ex}{1.1}{}{}"),
    ("\u01b6", r"\ipabar{z}{.5ex}{1.1}{}{}"),
    ("\u01b9", r"\textrevyogh{}"),
    ("\u01be", r"\textcrinvglotstop{}"),
    ("\u01c0", r"\textpipe{}"),
    ("\u01c1", r"\textdoublepipe{}"),
    ("\u01c2", r"\textdoublebarpipe{}"),
    ("\u01c3", r"!"),
    ("\u01c4", r"D\v{Z}"),
    ("\u01c5", r"D\v{z}"),
    ("\u01c6", r"d\v{z}"),
    ("\u01c7", r"LJ"),
    ("\u01c8", r"Lj"),
    ("\u01c9", r"lj"),
    ("\u01ca", r"NJ"),
    ("\u01cb", r"Nj"),
    ("\u01cc", r"nj"),
    ("\u01cd", r"\v{A}"),
    ("\u01ce", r"\v{a}"),
    ("\u01cf", r"\v{I}"),
    ("\u01d0", r"\v{\i}"),
    ("\u01d1", r"\v{O}"),
    ("\u01d2", r"\v{o}"),
    ("\u01d3", r"\v{U}"),
    ("\u01d4", r"\v{u}"),
    ("\u01d5", r"\={\"U}"),
    ("\u01d6", r"\={\"u}"),
    ("\u01d7", r"\'{\"U}"),
    ("\u01d8", r"\'{\"u}"),
    ("\u01d9", r"\v{\"U}"),
    ("\u01da", r"\v{\"u}"),
    ("\u01db", r"\`{\"U}"),
    ("\u01dc", r"\`{\"u}"),
    ("\u01dd", r"\textschwa{}"),
    ("\u01de", r"\={\"A}"),
    ("\u01df", r"\={\"a}"),
    ("\u01e0", r"\={\.A}"),
    ("\u01e1", r"\={\.a}"),
    ("\u01e2", r"\={\AE}"),
    ("\u01e3", r"\={\ae}"),
    ("\u01e6", r"\v{G}"),
    ("\u01e7", r"\v{g}"),
    ("\u01e8", r"\v{K}"),
    ("\u01e9", r"\v{k}"),
    ("\u01ea", r"\textpolhook{O}"),
    ("\u01eb", r"\textpolhook{o}"),
    ("\u01ec", r"\={\textpolhook{O}}"),
    ("\u01ed", r"\={\textpolhook{o}}"),
    ("\u01ef", r"\v{\textyogh}"),
    ("\u01f0", r"\v{\j}"),
    ("\u01f1", r"DZ"),
    ("\u01f2", r"Dz"),
    ("\u01f3", r"dz"),
    ("\u01f4", r"\'G"),
    ("\u01f5", r"\'g"),
    ("\u01fa", r"\'{\AA}"),
    ("\u01fb", r"\'{\aa}"),
    ("\u01fc", r"\'{\AE}"),
    ("\u01fd", r"\'{\ae}"),
    ("\u01fe", r"\'{\O}"),
    ("\u01ff", r"\'{\o}"),
    ("\u0200", r"\textdoublegrave{A}"),
    ("\u0201", r"\textdoublegrave{a}"),
    ("\u0202", r"\textroundcap{A}"),
    ("\u0203", r"\textroundcap{a}"),
    ("\u0204", r"\textdoublegrave{E}"),
    ("\u0205", r"\textdoublegrave{e}"),
    ("\u0206", r"\textroundcap{E}"),
    ("\u0207", r"\textroundcap{e}"),
    ("\u0208", r"\textdoublegrave{I}"),
    ("\u0209", r"\textdoublegrave{\i}"),
    ("\u020a", r"\textroundcap{I}"),
    ("\u020b", r"\textroundcap{\i}"),
    ("\u020c", r"\textdoublegrave{O}"),
    ("\u020d", r"\textdoublegrave{o}"),
    ("\u020e", r"\textroundcap{O}"),
    ("\u020f", r"\textroundcap{o}"),
    ("\u0210", r"\textdoublegrave{R}"),
    ("\u0211", r"\textdoublegrave{r}"),
    ("\u0212", r"\textroundcap{R}"),
    ("\u0213", r"\textroundcap{r}"),
    ("\u0214", r"\textdoublegrave{U}"),
    ("\u0215", r"\textdoublegrave{u}"),
    ("\u0216", r"\textroundcap{U}"),
    ("\u0217", r"\textroundcap{u}"),
    ("\u0250", r"\textturna{}"),
    ("\u0251", r"\textscripta{}"),
    ("\u0252", r"\textturnscripta{}"),
    ("\u0253", r"\texthtb{}"),
    ("\u0254", r"\textopeno{}"),
    ("\u0255", r"\textctc{}"),
    ("\u0256", r"\textrtaild{}"),
    ("\u0257", r"\texthtd{}"),
    ("\u0258", r"\textreve{}"),
    ("\u0259", r"\textschwa{}"),
    ("\u025a", r"\textrhookschwa{}"),
    ("\u025b", r"\textepsilon{}"),
    ("\u025c", r"\textrevepsilon{}"),
    ("\u025d", r"\textrhookrevepsilon{}"),
    ("\u025e", r"\textcloserevepsilon{}"),
    ("\u025f", r"\textObardotlessj{}"),
    ("\u0260", r"\texthtg{}"),
    ("\u0261", r"\textipa{g}"),
    ("\u0262", r"\textscg{}"),
    ("\u0263", r"\textgamma{}"),
    ("\u0264", r"\textbabygamma{}"),
    ("\u0265", r"\textturnh{}"),
    ("\u0266", r"\texthth{}"),
    ("\u0267", r"\texththeng{}"),
    ("\u0268", r"\textbari{}"),
    ("\u0269", r"\textiota{}"),
    ("\u026a", r"\textsci{}"),
    ("\u026b", r"\textltilde{}"),
    ("\u026c", r"\textbeltl{}"),
    ("\u026d", r"\textrtaill{}"),
    ("\u026f", r"\textturnm{}"),
    ("\u0270", r"\textturnmrleg{}"),
    ("\u0271", r"\textltailm{}"),
    ("\u0272", r"\textltailn{}"),
    ("\u0273", r"\textrtailn{}"),
    ("\u0274", r"\textscn{}"),
    ("\u0275", r"\textbaro{}"),
    ("\u0276", r"\textscoelig{}"),
    ("\u0277", r"\textcloseomega{}"),
    ("\u0278", r"\textphi{}"),
    ("\u0279", r"\textturnr{}"),
    ("\u027a", r"\textturnlonglegr{}"),
    ("\u027b", r"\textturnrrtail{}"),
    ("\u027c", r"\textlonglegr{}"),
    ("\u027d", r"\textrtailr{}"),
    ("\u027e", r"\textfishhookr{}"),
    ("\u0280", r"\textscr{}"),
    ("\u0281", r"\textinvscr{}"),
    ("\u0282", r"\textrtails{}"),
    ("\u0283", r"\textesh{}"),
    ("\u0284", r"\textdoublebaresh{}"),
    ("\u0286", r"\textctesh{}"),
    ("\u0287", r"\textturnt{}"),
    ("\u0288", r"\textrtailt{}"),
    ("\u0289", r"\textbaru{}"),
    ("\u028a", r"\textupsilon{}"),
    ("\u028b", r"\textscriptv{}"),
    ("\u028c", r"\textturnv{}"),
    ("\u028d", r"\textturnw{}"),
    ("\u028e", r"\textturny{}"),
    ("\u028f", r"\textscy{}"),
    ("\u0290", r"\textrtailz{}"),
    ("\u0291", r"\textctz{}"),
    ("\u0292", r"\textyogh{}"),
    ("\u0293", r"\textctyogh{}"),
    ("\u0294", r"\textglotstop{}"),
    ("\u0295", r"\textrevglotstop{}"),
    ("\u0296", r"\textinvglotstop{}"),
    ("\u0297", r"\textstretchc{}"),
    ("\u0298", r"\textbullseye{}"),
    ("\u0299", r"\textscb{}"),
    ("\u029a", r"\textcloseepsilon{}"),
    ("\u029b", r"\texthtscg{}"),
    ("\u029c", r"\textsch{}"),
    ("\u029d", r"\textctj{}"),
    ("\u029e", r"\textturnk{}"),
    ("\u029f", r"\textscl{}"),
    ("\u02a0", r"\texthtq{}"),
    ("\u02a1", r"\textbarglotstop{}"),
    ("\u02a2", r"\textbarrevglotstop{}"),
    ("\u02a3", r"\textdzlig{}"),
    ("\u02a4", r"\textdyoghlig{}"),
    ("\u02a5", r"\textdctzlig{}"),
    ("\u02a6", r"\texttslig{}"),
    ("\u02a7", r"\textteshlig{}"),
    ("\u02a8", r"\texttctclig{}"),
    ("\u02b0", r"\textsuperscript{h}"),
    ("\u02b1", r"\textsuperscript{\texthth}"),
    ("\u02b2", r"\textsuperscript{j}"),
    ("\u02b3", r"\textsuperscript{r}"),
    ("\u02b4", r"\textsuperscript{\textturnr}"),
    ("\u02b5", r"\textsuperscript{\textturnrrtail}"),
    ("\u02b6", r"\textsuperscript{\textinvscr}"),
    ("\u02b7", r"\textsuperscript{w}"),
    ("\u02b8", r"\textsuperscript{y}"),
    ("\u02b9", r"\textceltpal{}"),
    ("\u02ba", r"\textceltpal\textceltpal{}"),
    ("\u02e5", r"\tone{55}"),
    ("\u02e6", r"\tone{44}"),
    ("\u02e7", r"\tone{33}"),
    ("\u02e8", r"\tone{22}"),
    ("\u02e9", r"\tone{11}"),
    ("\u2010", r"-"),
    ("\u2011", r"-"),
    ("\u2012", r"--"),
    ("\u2013", r"--"),
    ("\u2014", r"---"),
    ("\u2018", r"`"),
    ("\u2019", r"'"),
    ("\u201a", r"\quotesinglbase{}"),
    ("\u201c", r"``"),
    ("\u201d", r"''"),
    ("\u201e", r"\quotedblbase{}"),
    ("\u2020", r"\dag{}"),
    ("\u2021", r"\ddag{}"),
    ("\u2022", r"\textbullet{}"),
    ("\u2024", r"."),
    ("\u2025", r".."),
    ("\u2026", r"\ldots{}"),
    ("\u2027", r"\textperiodcentered{}"),
    ("\u2030", r"\textperthousand{}"),
    ("\u2031", r"\textpertenthousand{}"),
    ("\u2032", r"\ensuremath{\prime}"),
    ("\u2033", r"\ensuremath{\prime\prime}"),
    ("\u2034", r"\ensuremath{\prime\prime\prime}"),
    ("\u2039", r"\guilsinglleft{}"),
    ("\u203a", r"\guilsinglright{}"),
    ("\u203b", r"\textreferencemark{}"),
    ("\u203c", r"!!"),
    ("\u203d", r"\textinterrobang{}"),
    ("\u203e", r"\textmacron{}"),
    ("\u2045", r"\textlquill{}"),
    ("\u2046", r"\textrquill{}"),
    ("\u20ac", r"\euro{}"),
    ("\u2100", r"\ensuremath{{}^a\!/\!_c}"),
    ("\u2101", r"\ensuremath{{}^a\!/\!_s}"),
    ("\u2105", r"\ensuremath{{}^c\!/\!_o}"),
    ("\u2106", r"\ensuremath{{}^c\!/\!_u}"),
    ("\u2116", r"N\textordmasculine{}"),
    ("\u2120", r"\textservicemark{}"),
    ("\u2121", r"\ensuremath{{}^\mathrm{TEL}}"),
    ("\u2122", r"\texttrademark{}"),
    ("\u2135", r"\ensuremath{\aleph}"),
    ("\u2153", r"\ensuremath{{}^1\!/\!_3}"),
    ("\u2154", r"\ensuremath{{}^2\!/\!_3}"),
    ("\u2155", r"\ensuremath{{}^1\!/\!_5}"),
    ("\u2156", r"\ensuremath{{}^2\!/\!_5}"),
    ("\u2157", r"\ensuremath{{}^3\!/\!_5}"),
    ("\u2158", r"\ensuremath{{}^4\!/\!_5}"),
    ("\u2159", r"\ensuremath{{}^1\!/\!_6}"),
    ("\u215a", r"\ensuremath{{}^5\!/\!_6}"),
    ("\u215b", r"\ensuremath{{}^1\!/\!_8}"),
    ("\u215c", r"\ensuremath{{}^3\!/\!_8}"),
    ("\u215d", r"\ensuremath{{}^5\!/\!_8}"),
    ("\u215e", r"\ensuremath{{}^7\!/\!_8}"),
    ("\u215f", r"\ensuremath{{}^1\!/}"),
    ("\u2160", r"I"),
    ("\u2161", r"II"),
    ("\u2162", r"III"),
    ("\u2163", r"IV"),
    ("\u2164", r"V"),
    ("\u2165", r"VI"),
    ("\u2166", r"VII"),
    ("\u2167", r"VIII"),
    ("\u2168", r"IX"),
    ("\u2169", r"X"),
    ("\u216a", r"XI"),
    ("\u216b", r"XII"),
    ("\u216c", r"L"),
    ("\u216d", r"C"),
    ("\u216e", r"D"),
    ("\u216f", r"M"),
    ("\u2170", r"i"),
    ("\u2171", r"ii"),
    ("\u2172", r"iii"),
    ("\u2173", r"iv"),
    ("\u2174", r"v"),
    ("\u2175", r"vi"),
    ("\u2176", r"vii"),
    ("\u2177", r"viii"),
    ("\u2178", r"ix"),
    ("\u2179", r"x"),
    ("\u217a", r"xi"),
    ("\u217b", r"xii"),
    ("\u217c", r"l"),
    ("\u217d", r"c"),
    ("\u217e", r"d"),
    ("\u217f", r"m"),
    ("\ufb00", r"ff"),
    ("\ufb01", r"fi"),
    ("\ufb02", r"fl"),
    ("\ufb03", r"ffi"),
    ("\ufb04", r"ffl"),
]

map_utf8_to_latex = dict(table)
map_latex_to_utf8 = dict([(l, u) for u, l in table])


if __name__ == "__main__":
    value = r"""Pr{\"u}fer, Kay and de Filippo, Cesare and Grote, Steffi and
              Mafessoni, Fabrizio and Korlevi{\'c}, Petra and Hajdinjak, Mateja
              and Vernot, Benjamin and Skov, Laurits and Hsieh, Pinghsun and
              Peyr{\'e}gne, St{\'e}phane and Reher, David and Hopfe, Charlotte
              and Nagel, Sarah and Maricic, Tomislav and Fu, Qiaomei and
              Theunert, Christoph and Rogers, Rebekah and Skoglund, Pontus and
              Chintalapati, Manjusha and Dannemann, Michael and Nelson, Bradley
              J and Key, Felix M and Rudan, Pavao and Ku{\'c}an, {\v Z}eljko
              and Gu{\v s}i{\'c}, Ivan and Golovanova, Liubov V and Doronichev,
              Vladimir B and Patterson, Nick and Reich, David and Eichler, Evan
              E and Slatkin, Montgomery and Schierup, Mikkel H and Andr{\'e}s,
              Aida M and Kelso, Janet and Meyer, Matthias and P{\"a}{\"a}bo,
              Svante"""
    utf8 = from_latex_to_utf8(value)
    print(utf8)
    latex = from_utf8_to_latex(utf8)
    print(latex)
    new_utf8 = from_latex_to_utf8(latex)
    print(utf8 == new_utf8)
