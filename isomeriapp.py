import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import datetime
import zipfile
import base64

#
# READ FILES
activities = pd.read_csv('atividades.csv', index_col=0)
progression = pd.read_csv('progressao.csv')
element_list = pd.read_csv('elementlist.csv', names=['M', 'element_initial', 'element'])

#
# FUNCTIONS
@st.cache(allow_output_mutation=True)
def open_zip(uploaded_zip):
    """Open the uploaded zip file, convert it's csv files to dataframes and stores them in a dictionnary where
    keys are the player name and elements are the dataframes.
    """
    z = zipfile.ZipFile(uploaded_zip)
    playerData={csv[:-4]: pd.read_csv(z.open(csv), index_col=0) for csv in z.namelist()}
    z.close()
    return playerData

def getMemberInfo():
    """Return a dataframe with member's name and function
    """
    z = zipfile.ZipFile(uploaded_zip)
    memberInfo = pd.read_csv(z.open('membros.csv'), index_col=0)
    z.close()
    return memberInfo

def getPlayerNames(playerData):
    """Return a list with sorted player names from the playerData dictionary
    """
    playerList = list(playerData.keys())[:]
    playerList.sort()
    playerList.remove('membros')
    return playerList

def activityToPointsMapper(selectedPlayer):
    """Return a dataframe with points mapped from activities realized by player
    """
    mappedPoints = playerData[selectedPlayer].apply(lambda activity: activity.array*activities['Pontos'], axis=1)
    return mappedPoints

def getTotalXP(mappedPoints):
    """Return total XP for a player from the mappedpoints as a single integer
    """
    totalXP = mappedPoints.sum().sum()
    return totalXP

def getLevel(totalXP):
    """Return level for a player based on the total XP
    """
    level = progression[progression['xp'] <= totalXP]['nivel'].max()
    return level

def getNextLevelXP(xp_level):
    """Return remaining XP for next level
    """
    nextXP = progression[progression['nivel'] > xp_level[1]]['xp'].min()
    diffXP = nextXP - xp_level[0]
    return diffXP

def getRanking(level):
    """Return ranking for a player based on his level
    """
    rank = element_list[element_list['M'] == level]['element'].array[0]
    return rank

@st.cache(allow_output_mutation=True)
def summaryTable(oldsummary=None, kind='first_run'):
    """Return summary table with all members name, function, XP, level and ranking.
    kind='first_run' gets the member info from the zip file. Otherwise, it updates the summary from the existing one.
    This is used to set new  XP, level and ranking from modified data in the 'Editar' page
    """
    if kind=='first_run':
        memberInfo = getMemberInfo()
    elif kind=='update':
        memberInfo = oldsummary
    memberInfo['XP'] = memberInfo['Nome'].map(lambda player: getTotalXP(activityToPointsMapper(player)))
    memberInfo['Level'] = memberInfo['XP'].map(lambda xp: getLevel(xp))
    memberInfo['Ranking'] = memberInfo['Level'].map(lambda level: getRanking(level))
    memberInfo['XP para próximo level'] = memberInfo[['XP','Level']].apply(getNextLevelXP, axis=1)
    memberInfo.sort_values(by='Level', inplace=True, ascending=False)   
    global summary
    summary = memberInfo
    return summary

def playerInfo(selectedPlayer):
    """Return row with player Name, Function, XP, Ranking and XP to next level
    """
    selectedPlayerInfo = summary[summary['Nome'] == selectedPlayer].set_index('Nome')
    return selectedPlayerInfo

def updatePlayerActivity(selectedPlayer, playerActivitySelector, date, kind='update'):
    """Update the player activity .csv table with a new activities row and alter the .zip file.
    kind='describe' is used to print the new activities so user can confirm changes.
    kind='update' updates the .csv and .zip files.
    """
    newActivities = pd.DataFrame(playerActivitySelector, index=[date.strftime('%Y-%m-%d')])
    if kind=='describe':
        return newActivities.T
    newActivities.columns = np.arange(0,10).astype('str')
    playerData[selectedPlayer] = pd.concat([playerData[selectedPlayer], newActivities])
    with zipfile.ZipFile(uploaded_zip, 'w') as csv_zip:
        memberInfo = getMemberInfo()
        for player in playerList:
            csv_zip.writestr(player+'.csv', playerData[player].to_csv())
        csv_zip.writestr('membros.csv', memberInfo.to_csv())

def get_zip_download_link(date): #downloadZip, date):
    """Generates a link allowing the data in a given ZIP file to be downloaded
    in:  cached zip file
    out: href string
    """
    b64 = base64.b64encode(uploaded_zip.getvalue()).decode() # bytes conversions necessary here
    ziphref = f'<strong><a href="data:file/zip;base64,{b64}" download="'+date.strftime('%d/%m/%Y')+'-weeklyData.zip">Download do arquivo .zip</a></strong>'
    return ziphref

def get_csv_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<strong><a href="data:file/csv;base64,{b64}" download="summary.csv">Download do Resumo</a></strong>'
    return href

def getAvailableDates(selectedPlayer=None, kind='all'):
    """Get all available dates from the players data.
    kind='all' return available dates for all players
    kind='individual' return available dates for selected player
    """
    alldates=[]
    if kind=='all':
        players = getPlayerNames(playerData)
    elif kind=='individual':
        players = [selectedPlayer]
    for player in players:
        for dates in playerData[player].index:
            alldates.append(pd.to_datetime(dates).strftime('%d/%m/%y'))    
    availableDates = pd.Series(alldates).unique()
    return availableDates

def getTotalActivity():
    """Get week activities for all players for the whole period.
    """
    players = getPlayerNames(playerData)
    totalActivity = pd.DataFrame()
    for player in players:
        totalActivity = totalActivity.append(playerData[player])
    totalActivity = totalActivity.astype('int8')
    totalActivity.columns = activities['Atividades'].array
    return totalActivity
    
def getWeekActivity(date, selectedPlayer=None, kind='all'):
    """Get weekly player activities for the selected date.
    kind='all' returns all players' activities along with a list of players that do not have the information for that date and a warningStatus (bool) that triggers the app's warning about these players.
    kind='individual' returns the selectedPlayer week activity for the date.
    """
    if kind=='all':
        players = getPlayerNames(playerData)
    elif kind=='individual':
        players = [selectedPlayer]
    week = date
    weekActivity = pd.DataFrame()
    playersWithoutData = []
    for player in players:
        try: # necessary if not all players have data for the date recorded.
            weekActivity = weekActivity.append(playerData[player].loc[week, :])
        except:
            playersWithoutData.append(player)
    weekActivity = weekActivity.astype('int8')
    warningStatus = (len(playersWithoutData) != 0)
    weekActivity.columns = activities['Atividades'].array
    if kind=='all':
        return weekActivity, playersWithoutData, warningStatus
    elif kind=='individual':
        return weekActivity.iloc[0]

def getMean(weekActivity):
    """Return a pandas series with the mean number of times each activity was executed.
    """
    mean = weekActivity.mean()
    return mean

def barplot(df, date=None, selectedPlayer=None, kind='total'):
    """Create activities barplot.
    kind='total' returns a barplot with x-label indicating the average is for the whole period
    kind='weekly' returns a barplot with x-label indicating the average is for a specific week
    """
    df = df.reset_index()
    df['XP da atividade'] = activities['Pontos']
    df.columns = ['Atividades', ' ', 'XP da atividade']
    if kind=='total':        
        title = 'Número médio de atividades realizadas em todo o período'
    elif kind=='weekly':
        title = 'Número médio de atividades realizadas na semana de {}'.format(
            pd.to_datetime(date, format='%d/%m/%y').strftime('%d/%m'))
        if selectedPlayer is not None:
            title = 'Atividades realizadas na semana de {} - {}'.format(
            pd.to_datetime(date, format='%d/%m/%y').strftime('%d/%m'), selectedPlayer)
    bars = alt.Chart(df, title=title).mark_bar(
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X(df.columns[1]+':Q', axis=alt.Axis(tickMinStep=1)),
        y=alt.Y(df.columns[0]+':N', sort='color'),
        color=alt.Color(df.columns[2]+':O', scale=alt.Scale(scheme="plasma"))
    )
    text = bars.mark_text(
        align='left',
        baseline='middle',
        dx=3  # Nudges text to right so it doesn't appear on top of the bar
    ).encode(
        text=alt.Text(df.columns[1]+':Q', format='.2')
    )
    barplot = (bars+text).properties(width = 797, height=400)
    return barplot

def XPlineplot(selectedPlayer):
    """Create individual player XP line plot.
    """
    plotdata = activityToPointsMapper(selectedPlayer).sum(axis=1).reset_index()
    plotdata.columns = ['semana', 'XP']
    plotdata['semana'] = plotdata['semana'].apply(pd.to_datetime)
    XPlineplot = alt.Chart(
        plotdata,
        width = 697, height=400,
        title='XP semanal - {}'.format(selectedPlayer)
    ).mark_area(
        point={'color':'#744a98', 'size':70},
        line={'color':'#744a98'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#23ac76', offset=0),
                   alt.GradientStop(color='#23ac7640', offset=1)],
            x1=1.5,
            x2=1.25,
            y1=1,
            y2=0.1
        )).encode(
        alt.X('semana:T', axis=alt.Axis(values=list(plotdata['semana'].array), format='%d/%m', grid=False)),
        alt.Y('XP:Q')
    )
    return XPlineplot    

#
# SIDEBAR

# Add text to the sidebar:
add_text = st.sidebar.markdown('### Bem vindo!')

# Add file uploader to the sidebar:
uploaded_zip = st.sidebar.file_uploader("Escolha sua coleção de arquivos (.zip):", type="zip")
if uploaded_zip is not None:
    playerData = open_zip(uploaded_zip)
    playerList = getPlayerNames(playerData)
    summary = summaryTable(kind='first_run')
    
# Add a selectbox to the sidebar:
add_selectbox = st.sidebar.selectbox(
    'O que vai ser hoje?',
    ('Sobre', 'Editar', 'Visualizar','Autor')
)

# Add image to the sidebar:
st.sidebar.image('Mascote.png', caption='Carbonito, o mascote da Isomeria', use_column_width=True)

#
# MAIN
def main():
    st.image('MK-Logo-Site.png')
    st.title('WebApp Isomeria - Soluções em Química')
    
    # SOBRE
    if add_selectbox == 'Sobre':
        st.header('Sobre')
        st.markdown('Este WebApp é utilizado pelos membros da **Isomeria** para atualizar e visualizar dados relativos a atividade semanal dos alunos participantes! [Saiba mais sobre nós!](http://www.quimica.ufpr.br/paginas/isomeria/)'
                   )
        st.markdown('____')
        st.header('Resumo dos jogadores')
        if uploaded_zip is not None:
            st.table(summary.set_index('Nome'))
            st.markdown(get_csv_download_link(summary), unsafe_allow_html=True)
        else:
            st.markdown('**Oops! O arquivo .zip não foi enviado!**')      
        st.markdown('____')
        st.subheader('Como utilizar o WebApp')
        st.markdown('Através da barra lateral, envie o arquivo .zip que contém as contagens de atividades semanais de cada jogador bem como suas respectivas funções. Então terá duas opções:'
                   )
        st.markdown('* Selecione **Editar** e use os controles para adicionar atividades a cada jogador. *O **recomendado** é inserir as atividades de cada participante ao fim de cada semana, **na mesma data**.*'
                   )
        st.markdown('* Ao final da edição de atividades para cada jogador, será disponibilizado um link de download para um arquivo .zip com os dados já atualizados.* **Ao editar os dados de atividade para o último jogador, tenha certeza de fazer o download deste arquivo para utilização posterior!** *Selecione **Visualizar** para obter gráficos gerais e de cada jogador através dos dados atualizados.'
                   )
        st.markdown('* Também é possível salvar a tabela de resumo acima através do botão de download a qualquer instante! As modificações para cada participante são sempre refletidas nessa tabela.'
                   )
        st.markdown('* Selecione **Visualizar** antes de Editar para obter gráficos gerais e de cada jogador a partir do .zip enviado, sem edições.'
                   )
        st.markdown('* Qualquer um dos gráficos gerados pode ser baixado através de suas opções (três pontos no canto superior direito do gráfico).'
                   )
        st.markdown('* O WebApp vai **guardar o estado das modificações feitas**, por isso, se deseja descartar modificações aperte **c** no teclado para limpar o cache e **r** para regarregar o app. Se quer enviar outro .zip, use **F5** no lugar de r.'
                   )
        st.markdown('* **Se observar erros**, tente limpar o cache referido anteriormente - **c** no teclado - e então recarregue o app com **F5**. Se persistir, entre em contato!'
                   )
        st.markdown('Para mais informações sobre o WebApp, código envolvido e para obter um **.zip de amostra**, acesse a aba **Autor**.'
                   )
        st.subheader('Níveis e Progressão')
        st.markdown('É utilizado um sistema de níveis, como em um jogo de RPG, onde os alunos adquirem experiência (XP) cada vez que realizam uma das atividades estabelecidas na tabela a seguir, que também apresenta a pontuação por atividade realizada.'
                   )
        st.table(activities.sort_values(by='Pontos').reset_index(drop=True))
        st.markdown('Esta experiência é resumida em rankings baseados no [número atômico de elementos químicos](https://pt.wikipedia.org/wiki/Tabela_peri%C3%B3dica) (1 - Hidrogênio, 2 - Hélio, ...), que podem ser visualizados aqui mesmo no WebApp!'
                   )

    # EDITAR
    if add_selectbox == 'Editar':
        st.header(add_selectbox)
        st.markdown('____')
        if uploaded_zip is not None:
            selectedPlayer = st.selectbox(
                'Os dados de que jogador serão atualizados?',
                (playerList)
            )
            date = st.date_input(
                'E qual a data?',
                value=datetime.date.today()
            )
            st.markdown('Modifique as atividades que desejar abaixo:')
            playerActivitySelector = {activity: st.number_input(activity,
                                                            min_value=0,
                                                            max_value=100,
                                                            value=0,
                                                            step=1)
                                  for activity in activities['Atividades']};            
            st.subheader('Informação atual:')
            selectedPlayerInfo = playerInfo(selectedPlayer)
            st.table(selectedPlayerInfo)
            st.subheader('Atividades a serem adicionadas:')
            st.table(updatePlayerActivity(selectedPlayer, playerActivitySelector, date, kind='describe'))
            st.write('Confirma e envia mudanças para {} na data de {}?'.format(selectedPlayer, date.strftime('%d/%m/%Y')))
            if st.button('SIM, MODIFIQUE!'):
                st.success('MODIFICADO COM SUCESSO! FAÇA DOWNLOAD OU CONTINUE A EDITAR!')
                updatePlayerActivity(selectedPlayer, playerActivitySelector, date)
                summaryTable(summary, kind='update')
                st.table(playerInfo(selectedPlayer))
                ziphref = get_zip_download_link(datetime.date.today())
                st.markdown(ziphref, unsafe_allow_html=True)
        else:
            st.markdown('**Oops! O arquivo .zip não foi enviado!**')
            
    # VISUALIZAR
    if add_selectbox == 'Visualizar':
        st.header(add_selectbox)
        st.markdown('____')
        if uploaded_zip is not None:
            st.header('Visualização Geral')
            availableDates = getAvailableDates(kind='all')
            try:
                st.subheader('Número médio de atividades realizadas no período de {} a {}'.
                             format(availableDates[0], availableDates[-1]))
            except:
                st.warning('Ainda não há atividades!') 
            totalMean = getMean(getTotalActivity())
            st.write(barplot(totalMean, kind='total'))
            st.subheader('Número médio de atividades realizadas por semana')            
            barplotDate = st.selectbox('Selecione a data da semana:',
                                       (availableDates), index=(len(availableDates)-1), key=1)
            try:
                weekActivity, playersWithoutData, warningStatus = getWeekActivity(
                    date=pd.to_datetime(barplotDate, format='%d/%m/%y').strftime('%Y-%m-%d'), kind='all')
                weekMean = getMean(weekActivity)
                st.write(barplot(weekMean, barplotDate, kind='weekly'))
                if warningStatus:
                    st.write('PS.: Os jogadores a seguir não tem dados para a data de {}:'.format(barplotDate), playersWithoutData)
            except:
                st.warning('Ainda não há atividades!')           
            st.markdown('____')
            st.header('Visualização Individual')
            selectedPlayer = st.selectbox(
                'Os dados de que jogador serão visualizados?',
                (playerList)
            )
            individualDates = getAvailableDates(selectedPlayer, kind='individual')
            individualBarplotDate = st.selectbox('Selecione a data da semana:',
                                       (individualDates), index=(len(individualDates)-1), key=2)
            st.subheader('Informação atual:')
            selectedPlayerInfo = playerInfo(selectedPlayer)
            st.table(selectedPlayerInfo)
            try:
                individualWeekActivity = getWeekActivity(
                    date=pd.to_datetime(individualBarplotDate, format='%d/%m/%y').strftime('%Y-%m-%d'),
                    selectedPlayer=selectedPlayer, kind='individual')
                st.write(barplot(individualWeekActivity, individualBarplotDate, selectedPlayer, kind='weekly'))
            except:
                st.warning('Ainda não há atividades!')
            st.write(XPlineplot(selectedPlayer))            
        else:
            st.markdown('**Oops! O arquivo .zip não foi enviado!**')

    # AUTOR
    if add_selectbox == 'Autor':
        st.header(add_selectbox)
        st.markdown('Este WebApp foi criado em Python por **Klismam** Franciosi Pereira, estudante e entusiasta do campo de ciência de dados e engenheiro ambiental formado pela UFPR.')
        st.markdown('O código deste WebApp e os seus requerimentos estão disponíveis em meu [Github](https://github.com/Key0412/webapp-isomeria/tree/master)! Lá você pode encontrar um [.zip de amostra](https://github.com/Key0412/webapp-isomeria/blob/master/SAMPLE.zip) para testar o WebApp.')
        st.markdown('Se tiver ideias de como melhorar este WebApp, se quiser criar um você mesmo, ou se tem uma ideia legal pra discutir, entre em contato!')
        st.subheader('Contatos')
        st.markdown('* [LinkedIn](https://www.linkedin.com/in/klismam-pereira/)')
        st.markdown('* [Github](https://github.com/Key0412)')
        st.markdown('* E-mail: kp.franciosi@gmail.com')
        
if __name__ == '__main__':
    main()