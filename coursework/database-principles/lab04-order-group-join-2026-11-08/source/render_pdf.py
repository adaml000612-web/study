from pathlib import Path
import pymupdf
from PIL import Image,ImageDraw
import sys
pdf=Path(sys.argv[1]); output=Path(sys.argv[2]); output.mkdir(parents=True,exist_ok=True)
d=pymupdf.open(pdf)
for i,page in enumerate(d):
    page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4),alpha=False).save(output/f'page-{i+1}.png')
for start in range(0,len(d),6):
    sheet=Image.new('RGB',(1260,1845),'#d8d8d8'); draw=ImageDraw.Draw(sheet)
    for n in range(start,min(start+6,len(d))):
        im=Image.open(output/f'page-{n+1}.png'); im.thumbnail((610,860))
        x=(n-start)%2*630+(630-im.width)//2; y=(n-start)//2*615
        im.thumbnail((420,585)); x=(n-start)%2*630+(630-im.width)//2
        sheet.paste(im,(x,y+25));draw.text((x,y+5),f'Page {n+1}',fill='black')
    sheet.save(output/f'contact-{start//6+1}.jpg')
print('pages',len(d))
