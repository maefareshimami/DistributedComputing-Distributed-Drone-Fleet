# DistributedComputing-Distributed-Drone-Fleet
> If you use my code or a part of it for your projects, thank you for quoting me!

Project team consisting of 4 people. Build a distributed drone fleet using MPI protocol.

The purpose of this project is to manipulate some basic notions of distributed algorithmic using the python programming language. The program displaying a window containing a drone that the user can control, clone that program *n* times, and make the clones successfully communicate with one another.

### Protocol
- Install the MPI protocol from the Microsoft's website.
- Put all files in a same folder and write `mpiexec -n 4 python main.py ping_1=n0 ping_2=n1 ping_3=n2 ping_4=n3` in your terminal.
Replace "n0", "n1", "n2", "n3" by the ping (in ms) you want for each drone.
