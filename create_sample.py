def create_sample():
    """Creates an empty, simple, sample to play around with in the WebApp
    """
    names = ['Marie Curie', 'Eistein', 'Isaac Newton', 'Galileu', 'Katherine Johnson']
    occupation = ['Cientista' for name in names]
    sampleData = {name:pd.DataFrame(columns=[str(x) for x in range(10)]) for name in names}
    sampleMembers = pd.DataFrame([names, occupation], index=['Nome', 'Cargo']).T
    with zipfile.ZipFile('SAMPLE.zip', 'w') as csv_zip:
        for name in names:
            csv_zip.writestr(name+'.csv', sampleData[name].to_csv())
        csv_zip.writestr('membros.csv', sampleMembers.to_csv())