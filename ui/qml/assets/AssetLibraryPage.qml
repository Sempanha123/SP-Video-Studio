import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase25 1.0
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"
Item {
    id: root
    signal toastRequested(string message,string variant)
    AssetImportDialog { id: importDialog }
    AssetPreviewDialog { id: previewDialog; parent:Overlay.overlay }
    AssetRelinkDialog { id: relinkDialog }
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        PageHeader { Layout.fillWidth: true; title: "Assets"; description: "Reusable media for every project. Drag into the Timeline or add it from a project.";
            actions: [
                AppButton { text: "Refresh"; variant: "quiet"; iconName: "refresh"; onClicked: AssetLibrary.refresh() },
                AppButton { text: "Import"; iconName: "plus"; shortcutHint:Commands.shortcutFor("asset.import"); onClicked: importDialog.openManaged() }
            ]
        }
        AssetFilterBar { id:filterBar; Layout.fillWidth: true; onQueryChanged: function(v){AssetLibrary.setQuery(v)}; onFilterChanged: function(v){AssetLibrary.setFilter(v)}; onSortChanged: function(v){AssetLibrary.setSort(v)} }
        SplitView { Layout.fillWidth: true; Layout.fillHeight: true
            AssetCollectionSidebar { SplitView.preferredWidth: 184; SplitView.minimumWidth: 150; collections: AssetLibrary.collections; onCollectionSelected: function(id){AssetLibrary.setCollection(id)} }
            AssetGrid { SplitView.fillWidth: true; SplitView.fillHeight: true; SplitView.minimumWidth: 420; assets: AssetLibrary.assets; hasMore: AssetLibrary.hasMore; onSelected: function(id){AssetLibrary.selectAsset(id)}; onLoadMoreRequested: AssetLibrary.loadMore(); onImportRequested: importDialog.openManaged() }
            AppCard { elevated: true; SplitView.preferredWidth: 292; SplitView.minimumWidth: 250; SplitView.maximumWidth: 380; SplitView.fillHeight: true; AssetInspector { anchors.fill: parent; anchors.margins: Theme.spacing.lg; asset: AssetLibrary.selectedAsset } }
        }
    }
    AppDialog { id:removeConfirm; parent:Overlay.overlay; width:420; header:null; footer:null; property string assetId:""; onOpened:Commands.setModalOpen(true); onClosed:Commands.setModalOpen(false)
        contentItem:ColumnLayout{spacing:Theme.spacing.md;Text{text:"Remove reusable asset?";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading}Text{Layout.fillWidth:true;text:"Referenced originals are never deleted from disk. Assets already used by projects require the Phase 25 safe-removal flow.";wrapMode:Text.WordWrap;color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall}RowLayout{Layout.fillWidth:true;Item{Layout.fillWidth:true}SecondaryButton{text:"Cancel";onClicked:removeConfirm.close()}AppButton{text:"Remove";variant:"danger";onClicked:{AssetLibrary.removeAsset(removeConfirm.assetId,"cancel");removeConfirm.close()}}}}
    }
    Connections { target:Commands; function onCommandRequested(commandId){
        if(Commands.activeContext!=="asset_library")return
        if(commandId==="asset.import")importDialog.openManaged()
        else if(commandId==="asset.search")filterBar.focusSearch()
        else if(commandId==="asset.preview"&&AssetLibrary.selectedAsset.id)previewDialog.showAsset(AssetLibrary.selectedAsset)
        else if(commandId==="asset.remove"&&AssetLibrary.selectedAsset.id){removeConfirm.assetId=AssetLibrary.selectedAsset.id;removeConfirm.open()}
        else if(commandId==="general.escape")Commands.setTextEditing(false)
    }}
    Connections { target: AssetLibrary; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} }
}
