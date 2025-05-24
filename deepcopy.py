a=[1,2,3,4]
b=a
print('before : \n a = ',a,'\nb = ',b)
a[0]=0
print('after : \n a = ',a,'\nb = ',b)

print('--------------------------------------------')
import copy
a=[1,2,3,4]
b=copy.deepcopy(a)
print('before : \n a = ',a,'\nb = ',b)
a[0]=0
print('after : \n a = ',a,'\nb = ',b)
