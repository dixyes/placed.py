
color_dict = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

class P ():
    def __init__(self,x,y):
        self.x=x
        self.y=y
    def __add__(self,other):
        return (self.x+other.x,self.y+other.y)
    def __iadd__(self,other):
        self.x += other.x
        self.y += other.y
        return self
    def __sub__(self,other):
        return (self.x-other.x,self.y-other.y)
    def __str__(self):
        return "(%d,%d)"%(self.x,self.y)
    __repr__ = __str__
    @property
    def t(self):
        return (self.x,self.y)

R = [
P(1,0),
P(0,-1),
P(-1,0),
P(0,1),
]

def hild(l:int,g="A",d=0):
    if l == 0:
        ret = []
        p = P(0,0)
        ret.append(p.t)
        #print(g.replace("A","").replace("B",""),l)
        for char in g:
            if char == "F":
                #print(char,":",p,"+",R[d],"=",p+R[d])
                p += R[d]
                ret.append(p.t)
            elif char == "+":
                d = (d+1) % 4
                #print(char,":turn to ",R[d])
            elif char == "-":
                d = (d-1) % 4
                #print(char,":turn to ",R[d])
        return ret
    else:
        return hild(l-1,g.replace("A","-XF+AFA+FX-").replace("B","+AF-BFB-FA+").replace("X","B"))


class HilbertCanvas():
    def __init__(self,level = 1,data = None):
        #print(data,level)
        if not data:
            self.level = level
            self._data = [ color_dict[0] for i in range(4**self.level)]
        else:
            self.level = int((len(data)-1).bit_length()/2)
            self._data = [ char for char in data ]
        self.canvas = hild(self.level)
        self.datalen = 4**self.level
        self.maplen = 2**self.level
    def set(self,x,y,c):
        if x > self.maplen or y > self.maplen or x <0 or y<0:
            raise Exception("out of index")
        if c in color_dict:
            self._data[self.canvas.index((x,y))] = c
    def setn(self,n,c):
        if n > self.datalen or n<0:
            raise Exception("out of index")
        if c in color_dict:
            self._data[n] = c
    def get(self,x,y):
        return self._data[self.canvas.index((x,y))]
    def getn(self,n):
        return self._data[n]
    def update(self):
        self.level += 1
        self.canvas = hild(self.level)
        self.datalen = 4**self.level
        neo = []
        for d in self._data:
            neo.extend([d,d,d,d])
        self._data = neo
    @property
    def data(self):
        return "".join(self._data)

if __name__ == "__main__":
    print(hild(3))
    hc = HilbertCanvas(3)
    hc.set(1,2,"3")
    print(hc.get(1,2))
    print(hc.data)
