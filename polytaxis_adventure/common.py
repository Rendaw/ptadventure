def limit(maxcount, generator):                                                 
    count = 0                                                                   
    for x in generator:                                                         
        if count >= maxcount:                                                   
            break                                                               
        count += 1                                                              
        yield x 

