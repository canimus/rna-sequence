using Pkg
Pkg.add(Pkg.PackageSpec(name="BGZFStreams", version="0.3.2"))
Pkg.add(Pkg.PackageSpec(name="GenomicFeatures", version="2.1.0"))
Pkg.add(Pkg.PackageSpec(name="GFF3", version="0.2.3"))
Pkg.add(Pkg.PackageSpec(name="Indexes", version="0.1.3"))
Pkg.add(Pkg.PackageSpec(name="StructArrays", version="0.6.17"))
Pkg.add(Pkg.PackageSpec(name="XAM", version="0.3.1"))
Pkg.add(Pkg.PackageSpec(name="BED", version="0.3.0"))
Pkg.add("ArgParse")
Pkg.add("Logging")
Pkg.precompile()
